import os
from fastapi import FastAPI, HTTPException
from web3 import Web3
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

# Конфигурация
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # Ключ админа

# Подключение к сети
w3 = Web3(Web3.HTTPProvider(RPC_URL))
contract_abi = [...]  # Вставьте ABI контракта PollSystem

poll_system = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
admin_address = w3.eth.account.from_key(PRIVATE_KEY).address

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
    return {"admin_address": admin_address}

@app.get("/polls")
async def get_polls():
    try:
        poll_ids = poll_system.functions.getAllPolls().call()
        polls = []
        for pid in poll_ids:
            poll = poll_system.functions.polls(pid).call()
            polls.append({
                "id": pid,
                "question": poll[0],
                "options": poll[1],
                "end_time": poll[2]
            })
        return polls
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-poll")
async def create_poll(request: CreatePollRequest):
    try:
        nonce = w3.eth.get_transaction_count(admin_address)
        tx = poll_system.functions.createPoll(
            request.question,
            request.options,
            request.duration
        ).build_transaction({
            'from': admin_address,
            'nonce': nonce,
            'gas': 2000000
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vote")
async def vote(request: VoteRequest):
    try:
        tx = poll_system.functions.voteWithSignature(
            request.poll_id,
            request.option_id,
            request.signature
        ).build_transaction({
            'from': admin_address,
            'nonce': w3.eth.get_transaction_count(admin_address)
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return {"tx_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)