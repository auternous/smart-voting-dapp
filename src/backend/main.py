import os
from fastapi import FastAPI, HTTPException
from web3 import Web3
#from web3.middleware.geth_poa import geth_poa_middleware
from dotenv import load_dotenv
from pydantic import BaseModel
from contract_abi import POLL_SYSTEM_ABI  # ABI PollSystem
import os

load_dotenv()

app = FastAPI()

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Конфиги
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
POLL_SYSTEM_ADDRESS = os.getenv("CONTRACT_ADDRESS")
POLL_TOKEN_ADDRESS = os.getenv("POLL_TOKEN_ADDRESS")

print("PRIVATE_KEY из .env:", PRIVATE_KEY)

# Подключаемся к Ethereum
w3 = Web3(Web3.HTTPProvider(RPC_URL))
#w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # если PoA сеть (например Hardhat)

# Адрес администратора из приватного ключа
account = w3.eth.account.from_key(PRIVATE_KEY)
ADMIN_ADDRESS = account.address

# Контракты
poll_system = w3.eth.contract(address=POLL_SYSTEM_ADDRESS, abi=POLL_SYSTEM_ABI)

ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_pollId", "type": "uint256"}],
        "name": "getPoll",
        "outputs": [
            {"internalType": "string", "name": "question", "type": "string"},
            {"internalType": "string[]", "name": "options", "type": "string[]"},
            {"internalType": "uint256", "name": "endTime", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "name": "transfer",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bool"}]
    }
]



poll_token = w3.eth.contract(address=POLL_TOKEN_ADDRESS, abi=ERC20_ABI)

# Запросы
class CreatePollRequest(BaseModel):
    question: str
    options: list[str]
    duration: int

class VoteRequest(BaseModel):
    poll_id: int
    option_id: int
    signature: str

class SignedVoteRequest(BaseModel):
    poll_id: int
    option_id: int
    signature: str
    voter_address: str

@app.get("/admin-address")
async def get_admin_address():
    return {"admin_address": ADMIN_ADDRESS}

@app.post("/relay-vote")
async def relay_vote(request: SignedVoteRequest):
    try:
        # Проверяем подпись
        message_hash = Web3.solidity_keccak(
            ['uint256', 'uint256', 'address'],
            [request.poll_id, request.option_id, request.voter_address]
        )
        recovered_address = w3.eth.account.recover_message(
            encode_defunct(message_hash),
            signature=request.signature
        )
        
        if recovered_address.lower() != request.voter_address.lower():
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Отправляем транзакцию через релейер
        tx = poll_system.functions.voteWithSignature(
            request.poll_id,
            request.option_id,
            request.voter_address,
            request.signature
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': w3.eth.get_transaction_count(ADMIN_ADDRESS),
            'gas': 200000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/polls")
async def get_polls():
    try:
        poll_ids = poll_system.functions.getAllPolls().call()
        polls = []
        for pid in poll_ids:
            question, options, end_time = poll_system.functions.getPoll(pid).call()

            print(f"[DEBUG] Poll {pid}: {question=} {type(question)=}")
            print(f"[DEBUG] Options: {options=} {type(options)=}")

            # Если вдруг question — байты, декодируем:
            if isinstance(question, bytes):
                question = question.decode("utf-8", errors="replace")

            decoded_options = []
            for opt in options:
                if isinstance(opt, bytes):
                    decoded_options.append(opt.decode("utf-8", errors="replace"))
                else:
                    decoded_options.append(opt)

            polls.append({
                "id": pid,
                "question": question,
                "options": decoded_options,
                "end_time": end_time
            })
        return polls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    try:
        block_number = w3.eth.block_number
        code = w3.eth.get_code(POLL_SYSTEM_ADDRESS)  # <-- используй POLL_SYSTEM_ADDRESS
        return {
            "block_number": block_number,
            "contract_code": code.hex(),
            "contract_code_empty": code == b""
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def approve_tokens_if_needed(spender, amount_wei):
    allowance = poll_token.functions.allowance(ADMIN_ADDRESS, spender).call()
    if allowance >= amount_wei:
        print("Approve уже установлен, пропускаем.")
        return None

    nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
    tx = poll_token.functions.approve(spender, amount_wei).build_transaction({
        'from': ADMIN_ADDRESS,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"Approve tx отправлен: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Approve tx в блоке: {receipt.blockNumber}")
    return receipt

# Примерная функция create_poll с 4 аргументами (если в контракте так)
@app.post("/create-poll")
async def create_poll(request: CreatePollRequest):
    try:
        amount_to_approve = w3.to_wei(1000, 'ether')
        balance = poll_token.functions.balanceOf(ADMIN_ADDRESS).call()
        if balance < amount_to_approve:
            raise HTTPException(status_code=400, detail="Недостаточно POLL токенов на балансе администратора")
        
        approve_receipt = approve_tokens_if_needed(POLL_SYSTEM_ADDRESS, amount_to_approve)
        if approve_receipt is not None:
            print("Approve выполнен, продолжаем с созданием опроса.")
        
        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

        # Если контракт ожидает 4 параметра (например, duration + minTokensRequired)
        min_tokens_required = w3.to_wei(10, 'ether')  # пример значения

        tx = poll_system.functions.createPoll(
            request.question,
            request.options,
            request.duration,
            min_tokens_required
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vote")
async def vote(request: VoteRequest):
    try:
        # Преобразуем hex строку подписи в bytes
        signature_bytes = bytes.fromhex(
            request.signature[2:] if request.signature.startswith('0x') 
            else request.signature
        )
        
        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
        tx = poll_system.functions.voteWithSignature(
            request.poll_id,
            request.option_id,
            signature_bytes  # Используем bytes вместо hex строки
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': nonce,
            #'gas': 200000,  # Добавляем лимит газа
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return {"tx_hash": tx_hash.hex()}
    except ValueError as e:
        if "Already voted" in str(e):
            raise HTTPException(status_code=400, detail="You have already voted in this poll")
        elif "Poll ended" in str(e):
            raise HTTPException(status_code=400, detail="This poll has already ended")
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
