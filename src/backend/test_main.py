import pytest
from fastapi.testclient import TestClient
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from models import SessionLocal, User, Poll, Vote
import time
from web3_setup import ADMIN

from main import app, poll_token, poll_system, w3
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_create_poll_invalid():
    response = client.post("/create-poll", json={
        "question": "",
        "options": ["Yes"],
        "duration": 0
    })
    assert response.status_code == 422

def test_invalid_signature():
    payload = {
        "poll_id": 0,
        "option_id": 1,
        "voter": "0x0000000000000000000000000000000000000000",
        "signature": "0xInvalidSignature"
    }
    response = client.post("/relay-vote", json=payload)
    assert response.status_code == 400

@pytest.fixture
def new_voter():
    acct = Account.create()
    return acct

def test_token_reward_on_vote(new_voter):
    # 1. Установка времени будущего блока
    future_time = w3.eth.get_block("latest")["timestamp"] + 60
    w3.provider.make_request("evm_setNextBlockTimestamp", [future_time])
    
    # 2. ЯВНО майним блок
    w3.provider.make_request("evm_mine", [])

    # 3. Теперь создаем опрос — он будет в fresh-блоке
    duration = 300  # 5 минут
    response = client.post("/create-poll", json={
        "question": "Test poll?",
        "options": ["Yes", "No"],
        "duration": duration
    })
    assert response.status_code == 200
    tx_hash = response.json()["tx_hash"]

    poll_id = 0
    option_id = 0
    voter = new_voter.address

    # 4. Проверка времени
    poll_contract_data = poll_system.functions.getPoll(poll_id).call()
    contract_end_time = poll_contract_data[2]
    now = w3.eth.get_block("latest")["timestamp"]
    print(f"[DEBUG] endTime: {contract_end_time}, now: {now}")
    assert now < contract_end_time, "Poll has already ended before vote!"

    # 5. Подпись
    message_hash = Web3.solidity_keccak(
        ["uint256", "uint256", "address"],
        [poll_id, option_id, voter]
    )
    signature = new_voter.sign_message(encode_defunct(message_hash)).signature.hex()

    # 6. Голосуем
    vote_response = client.post("/relay-vote", json={
        "poll_id": poll_id,
        "option_id": option_id,
        "voter": voter,
        "signature": signature
    })

    print(f"[DEBUG] Vote response: {vote_response.status_code} - {vote_response.text}")
    assert vote_response.status_code == 200



def test_create_user_manually():
    session = SessionLocal()
    test_wallet = "0xAbcdef123456789000000000000000000000dEaD"

    # Удаляем, если был
    session.query(User).filter_by(address=test_wallet).delete()
    session.commit()

    # Добавляем нового пользователя
    user = User(address=test_wallet)
    session.add(user)
    session.commit()

    # Проверяем из базы
    u = session.query(User).filter_by(address=test_wallet).first()
    assert u is not None
    assert u.polls_created == 0
    assert u.votes_cast == 0
    session.close()

def test_get_balance():
    response = client.get(f"/balance/{ADMIN}")
    assert response.status_code == 200
    data = response.json()
    assert data["address"].lower() == ADMIN.lower()
    assert "balance" in data
    assert isinstance(data["balance"], int)
    assert data["symbol"] == "POLL"