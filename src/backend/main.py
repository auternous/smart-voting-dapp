from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
from web3 import Web3
from eth_account.messages import encode_defunct
from fastapi.middleware.cors import CORSMiddleware
from web3_setup import w3, poll_system, poll_token, ADMIN, PRIVATE_KEY
from models import SessionLocal, User, Poll, Vote
from schemas import CreatePoll, RelayVoteRequest
from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Получаем данные опроса из контракта
def get_contract_poll(poll_id: int):
    try:
        question, options, end_time_raw = poll_system.functions.getPoll(poll_id).call()
        end_time = int(end_time_raw)

        # 🛡️ Защищённый вызов getVotes
        try:
            votes = poll_system.functions.getVotes(poll_id).call()
        except Exception as e:
            print(f"⚠️ Голоса не получены для poll #{poll_id}: {e}")
            votes = None

        return {
            "id": poll_id,
            "question": question,
            "options": options,
            "end_time": end_time,
            "votes": votes,  # может быть None, фронт обработает
        }
    except Exception as e:
        print(f"❌ Ошибка при получении poll #{poll_id}: {e}")
        return None


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "block": w3.eth.block_number,
        "admin": ADMIN
    }



@app.get("/leaderboard")
def get_leaderboard():
    session = SessionLocal()
    try:
        users = session.query(User).all()
        result = []

        for user in users:
            try:
                checksum = Web3.to_checksum_address(user.address)
                balance_raw = poll_token.functions.balanceOf(checksum).call()
                decimals = poll_token.functions.decimals().call()
                balance = balance_raw // (10 ** decimals)

                result.append({
                    "address": checksum,
                    "balance": balance
                })
            except Exception as e:
                print(f"⚠️ Не удалось получить баланс для {user.address}: {e}")
                continue

        sorted_result = sorted(result, key=lambda x: x["balance"], reverse=True)
        return sorted_result[:10]
    finally:
        session.close()


@app.get("/balance/{address}")
def get_balance(address: str):
    try:
        checksum = Web3.to_checksum_address(address)
        balance = poll_token.functions.balanceOf(checksum).call()
        return {
            "address": checksum,
            "balance": balance,
            "symbol": poll_token.functions.symbol().call(),
            "decimals": poll_token.functions.decimals().call()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/polls")
def get_polls():
    try:
        ids = poll_system.functions.getAllPollIds().call()
        return [get_contract_poll(pid) for pid in ids]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-poll")
def create_poll(req: CreatePoll):
    try:
        fee = w3.to_wei(100, "ether")
        balance = poll_token.functions.balanceOf(ADMIN).call()
        if balance < fee:
            raise HTTPException(status_code=400, detail="Not enough POLL tokens")

        allowance = poll_token.functions.allowance(ADMIN, poll_system.address).call()
        if allowance < fee:
            nonce = w3.eth.get_transaction_count(ADMIN)
            approve_tx = poll_token.functions.approve(poll_system.address, fee).build_transaction({
                "from": ADMIN,
                "nonce": nonce,
                "gasPrice": w3.to_wei("20", "gwei")
            })
            signed = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
            w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(signed.hash)

        nonce = w3.eth.get_transaction_count(ADMIN)
        tx = poll_system.functions.createPoll(req.question, req.options, req.duration).build_transaction({
            "from": ADMIN,
            "nonce": nonce,
            "gasPrice": w3.to_wei("20", "gwei"),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        logs = poll_system.events.PollCreated().process_receipt(receipt)
        poll_id = logs[0]['args']['pollId']
        poll_data = get_contract_poll(poll_id)

        session = SessionLocal()
        user = session.get(User, ADMIN)
        if not user:
            user = User(address=ADMIN)
            session.add(user)

        db_poll = Poll(
            question=poll_data['question'],
            options=poll_data['options'],
            end_time=poll_data['end_time'],
            creator_address=ADMIN,
            created_at=datetime.now(timezone.utc)
        )
        session.add(db_poll)
        user.polls_created += 1
        session.commit()
        session.close()

        return {"tx_hash": tx_hash.hex(), "poll_id": poll_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import Body

@app.post("/relay-vote")
def relay_vote(req: RelayVoteRequest = Body(...)):
    try:
        # ✅ Явно валидируем hex подпись
        try:
            signature_bytes = bytes.fromhex(req.signature[2:] if req.signature.startswith("0x") else req.signature)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex signature")

        # 🧮 Сборка сообщения
        message_hash = Web3.solidity_keccak(
            ["uint256", "uint256", "address"],
            [req.poll_id, req.option_id, Web3.to_checksum_address(req.voter)]
        )
        eth_signed = encode_defunct(message_hash)

        # ✅ Проверка подписи
        try:
            recovered = w3.eth.account.recover_message(eth_signed, signature=signature_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Signature validation failed")

        if recovered.lower() != req.voter.lower():
            raise HTTPException(status_code=400, detail="Signature does not match voter address")

        # 🌐 Отправка транзакции от релэера
        nonce = w3.eth.get_transaction_count(ADMIN)
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

        # 🗂️ Сохраняем результат в БД
        session = SessionLocal()
        user = session.get(User, req.voter)
        if not user:
            user = User(address=req.voter)
            session.add(user)

        user.votes_cast = (user.votes_cast or 0) + 1

        vote = Vote(
            poll_id=req.poll_id,
            option_id=req.option_id,
            user_address=req.voter,
            tx_hash=tx_hash.hex()
        )
        session.add(vote)
        session.commit()
        session.close()

        return {"tx_hash": tx_hash.hex()}

    except HTTPException as he:
        # Пропускаем HTTP ошибки напрямую
        raise he
    except Exception as e:
        # Все остальные ошибки → 500
        raise HTTPException(status_code=500, detail=str(e))