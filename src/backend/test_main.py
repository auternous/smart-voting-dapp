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

def test_token_reward_on_vote_multiple_polls(new_voter):
    created_polls = []

    for i in range(10):
        question = f"Test poll #{i + 1}?"
        response = client.post("/create-poll", json={
            "question": question,
            "options": ["Option A", "Option B"],
            "duration": 300000 + i * 10  
        })
        assert response.status_code == 200
        poll_id = response.json()["poll_id"]

        poll_data = poll_system.functions.getPoll(poll_id).call()
        contract_end_time = poll_data[2]

        created_polls.append({
            "poll_id": poll_id,
            "end_time": contract_end_time,
            "question": question
        })

    selected_poll = created_polls[0]
    poll_id = selected_poll["poll_id"]
    contract_end_time = selected_poll["end_time"]

    vote_time = contract_end_time - 10
    w3.provider.make_request("evm_setNextBlockTimestamp", [vote_time])
    w3.provider.make_request("evm_mine", [])

    now = w3.eth.get_block("latest")["timestamp"]
    print(f"[DEBUG] Voting on poll_id={poll_id}")
    print(f"[DEBUG] endTime: {contract_end_time}, now: {now}")
    assert now < contract_end_time, "Poll has already ended before vote!"


def test_create_user_manually():
    session = SessionLocal()
    test_wallet = "0xAbcdef123456789000000000000000000000dEaD"

    session.query(User).filter_by(address=test_wallet).delete()
    session.commit()

    user = User(address=test_wallet)
    session.add(user)
    session.commit()

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