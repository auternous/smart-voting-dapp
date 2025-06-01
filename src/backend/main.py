import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from web3 import Web3
from eth_account.messages import encode_defunct
from models import SessionLocal, User, Poll, Vote
from datetime import datetime, timedelta, timezone

# 🔌 ABI & deploy info
from contract_abi import POLL_SYSTEM_ABI, ERC20_ABI, DEPLOY_INFO

# 🔄 Загрузка переменных из .env
load_dotenv()

app = FastAPI()

# 🌿 Конфигурация из .env или fallback на deploy.json
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
SYSTEM_ADDRESS = os.getenv("CONTRACT_ADDRESS") or DEPLOY_INFO["pollSystemAddress"]
TOKEN_ADDRESS = os.getenv("POLL_TOKEN_ADDRESS") or DEPLOY_INFO["pollTokenAddress"]

# ⛓️ Подключение к сети + контрактам
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
ADMIN = account.address

poll_system = w3.eth.contract(address=SYSTEM_ADDRESS, abi=POLL_SYSTEM_ABI)
poll_token = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_ABI)

print(f"✅ Connected as: {ADMIN}")
print(f"📦 System Contract: {SYSTEM_ADDRESS}")
print(f"💰 Token Contract: {TOKEN_ADDRESS}")

# 🩺 ПИНГ
@app.get("/health")
def health_check():
    try:
        return {
            "status": "ok",
            "block": w3.eth.block_number,
            "admin": ADMIN,
            "system": SYSTEM_ADDRESS,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📋 ПОЛУЧИТЬ ВСЕ ОПРОСЫ
@app.get("/polls")
def get_polls():
    try:
        ids = poll_system.functions.getAllPollIds().call()
        polls = []
        for pid in ids:
            question, options, end_time = poll_system.functions.getPoll(pid).call()
            polls.append({
                "id": pid,
                "question": question,
                "options": options,
                "end_time": end_time,
            })
        return polls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🧾 Тип: создание опроса с валидацией
class CreatePoll(BaseModel):
    question: str = Field(..., min_length=1)
    options: list[str]
    duration: int = Field(..., gt=0)  # в секундах

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) < 2:
            raise ValueError("At least two options required")
        return v

# ➕ СОЗДАНИЕ ОПРОСА
@app.post("/create-poll")
def create_poll(req: CreatePoll):
    try:
        fee = w3.to_wei(100, "ether")

        # 1. Проверяем, если нужно — делаем approve()
        allowance = poll_token.functions.allowance(ADMIN, SYSTEM_ADDRESS).call()
        if allowance < fee:
            print(f"🛂 Approving {fee} tokens...")
            nonce = w3.eth.get_transaction_count(ADMIN)
            approve_tx = poll_token.functions.approve(
                SYSTEM_ADDRESS, fee
            ).build_transaction({
                "from": ADMIN,
                "nonce": nonce,
                "gasPrice": w3.to_wei("20", "gwei")
            })
            signed = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
            w3.eth.send_raw_transaction(signed.raw_transaction)
            print("✅ Approve sent")

        # 2. Сборка и отправка createPoll
        print(f"🗳️ Creating poll: {req.question}")
        nonce = w3.eth.get_transaction_count(ADMIN)
        create_tx = poll_system.functions.createPoll(
            req.question,
            req.options,
            req.duration
        ).build_transaction({
            "from": ADMIN,
            "nonce": nonce,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed_create = w3.eth.account.sign_transaction(create_tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_create.raw_transaction)
        print(f"✅ Poll created: {tx_hash.hex()}")

        # 3. Сохраняем в БД (голый лог — без end_time)
        session = SessionLocal()

        # Убедиться, что автор есть в БД
        user = session.get(User, ADMIN)
        if not user:
            user = User(address=ADMIN, polls_created=0)
            session.add(user)

        poll = Poll(
            question=req.question,
            options=req.options,
            creator_address=ADMIN,
            created_at=datetime.now(timezone.utc)
            # Не указываем end_time! `PollSystem.sol` сам рассчитывает
        )
        session.add(poll)

        user.polls_created = (user.polls_created or 0) + 1
        session.commit()
        session.close()

        return {"tx_hash": "0x" + tx_hash.hex()}

    except Exception as e:
        print("❌ Error in /create-poll:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
class RelayVoteRequest(BaseModel):
    poll_id: int
    option_id: int
    voter: str    # Адрес пользователя
    signature: str  # Подпись от фронта в hex


@app.post("/relay-vote")
def relay_vote(req: RelayVoteRequest):
    try:
        print(f"🔐 Проверка подписи от {req.voter}...")

        message_hash = Web3.solidity_keccak(
            ["uint256", "uint256", "address"],
            [req.poll_id, req.option_id, Web3.to_checksum_address(req.voter)]
        )

        eth_signed_message = encode_defunct(message_hash)
        recovered = w3.eth.account.recover_message(eth_signed_message, signature=req.signature)

        if recovered.lower() != req.voter.lower():
            raise HTTPException(status_code=400, detail="❌ Invalid signature")

        print("✅ Signature valid. Relaying vote...")

        nonce = w3.eth.get_transaction_count(ADMIN)
        signature_bytes = bytes.fromhex(req.signature[2:] if req.signature.startswith("0x") else req.signature)

        tx = poll_system.functions.voteWithSignature(
            req.poll_id,
            req.option_id,
            req.voter,
            signature_bytes
        ).build_transaction({
            "from": ADMIN,
            "nonce": nonce,
            "gasPrice": w3.to_wei("20", "gwei")
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

        session = SessionLocal()

        # Зарегистрировать нового пользователя, если не был
        user = session.get(User, req.voter)
        
        user = session.get(User, req.voter)
        if not user:
            user = User(
                address=req.voter,
                balance=0,
                polls_created=0,
                votes_cast=0
            )
            session.add(user)

        user.votes_cast += 1



        vote = Vote(
            poll_id=req.poll_id,
            option_id=req.option_id,
            user_address=req.voter,
            tx_hash="0x" + tx_hash.hex()
        )
        session.add(vote)
        session.commit()
        session.close()

        return {"tx_hash": "0x" + tx_hash.hex()}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex signature")

    except Exception as e:
        print("❌ Error relaying vote:", str(e))
        raise HTTPException(status_code=500, detail=str(e))