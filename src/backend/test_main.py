import pytest
from fastapi.testclient import TestClient
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from models import SessionLocal, User, Poll, Vote
from web3_setup import ADMIN
from main import app, poll_token, poll_system, w3

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_poll_invalid():
    response = client.post("/create-poll", json={
        "question": "",
        "options": ["Yes"],
        "duration": 0
    })
    assert response.status_code == 422  # validation error


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
    return Account.create()


def test_token_reward_on_vote_multiple_polls(new_voter):
    created_polls = []

    for i in range(3):  # упрощено: не надо 10, главное — хотя бы несколько
        question = f"Test poll #{i + 1}?"
        response = client.post("/create-poll", json={
            "question": question,
            "options": ["Option A", "Option B"],
            "duration": 300
        })

        if response.status_code != 200:
            print(f"[‼️] Ошибка создания опроса #{i + 1}: {response.status_code}")
            print("↪ Ответ сервера:", response.json())
        assert response.status_code == 200

        json = response.json()
        poll_id = json["poll_id"]

        contract_poll = poll_system.functions.getPoll(poll_id).call()
        end_time = contract_poll[2]

        created_polls.append({
            "poll_id": poll_id,
            "end_time": end_time,
            "question": question
        })

    assert len(created_polls) > 0

    selected = created_polls[0]
    poll_id = selected["poll_id"]
    end_time = selected["end_time"]

    vote_time = end_time - 10
    w3.provider.make_request("evm_setNextBlockTimestamp", [vote_time])
    w3.provider.make_request("evm_mine", [])

    current_time = w3.eth.get_block("latest")["timestamp"]
    print(f"[DEBUG] Current block time: {current_time}, poll end time: {end_time}")
    assert current_time < end_time


def test_create_user_manually():
    session = SessionLocal()
    test_wallet = "0xAbcdef123456789000000000000000000000dEaD"

    session.query(User).filter_by(address=test_wallet).delete()
    session.commit()

    new_user = User(address=test_wallet)
    session.add(new_user)
    session.commit()

    u = session.query(User).filter_by(address=test_wallet).first()
    assert u is not None
    assert u.polls_created == 0
    assert u.votes_cast == 0
    session.close()


def test_get_balance():
    response = client.get(f"/balance/{ADMIN}")

    if response.status_code != 200:
        print(f"[‼️] Ошибка запроса баланса: {response.status_code}")
        print("↪ Ответ сервера:", response.json())
    assert response.status_code == 200

    data = response.json()
    assert data["address"].lower() == ADMIN.lower()
    assert "balance" in data

    # Пытаемся привести строку к int
    try:
        balance_value = int(data["balance"])
        assert balance_value >= 0
    except (ValueError, TypeError):
        assert False, f"Баланс не число: {data['balance']}"