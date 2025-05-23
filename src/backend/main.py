import os
from fastapi import FastAPI, HTTPException
from web3 import Web3
#from web3.middleware.geth_poa import geth_poa_middleware
from dotenv import load_dotenv
from pydantic import BaseModel
from contract_abi import POLL_SYSTEM_ABI  # ABI PollSystem

load_dotenv()

app = FastAPI()

# Конфиги
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
POLL_SYSTEM_ADDRESS = os.getenv("CONTRACT_ADDRESS")
POLL_TOKEN_ADDRESS = os.getenv("POLL_TOKEN_ADDRESS")

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

@app.get("/admin-address")
async def get_admin_address():
    return {"admin_address": ADMIN_ADDRESS}

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

@app.post("/create-poll")
async def create_poll(request: CreatePollRequest):
    try:
        # Сумма токенов для approve — тут ставь ту, что требуется PollSystem, например 1000 POLL
        amount_to_approve = w3.to_wei(1000, 'ether')

        # Проверяем баланс, чтобы не сломать
        balance = poll_token.functions.balanceOf(ADMIN_ADDRESS).call()
        if balance < amount_to_approve:
            raise HTTPException(status_code=400, detail="Недостаточно POLL токенов на балансе администратора")

        # Делаем approve, если надо
        approve_receipt = approve_tokens_if_needed(POLL_SYSTEM_ADDRESS, amount_to_approve)
        if approve_receipt is not None:
            print("Approve выполнен, продолжаем с созданием опроса.")

        # Создаём опрос
        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
        tx = poll_system.functions.createPoll(
            request.question,
            request.options,
            request.duration
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
        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)
        tx = poll_system.functions.voteWithSignature(
            request.poll_id,
            request.option_id,
            request.signature
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': nonce,
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)


        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
