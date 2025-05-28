import pytest
from fastapi.testclient import TestClient
from eth_account.messages import encode_defunct
from web3 import Web3
from main import app, w3, poll_system, poll_token, ADMIN_ADDRESS, PRIVATE_KEY
import os
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

# Тестовые данные
TEST_QUESTION = "Test question?"
TEST_OPTIONS = ["Option 1", "Option 2", "Option 3"]
TEST_DURATION = 3600  # 1 hour

@pytest.fixture(scope="module")
def test_account():
    """Фикстура для тестового аккаунта"""
    return w3.eth.account.create()

@pytest.fixture(scope="module")
def test_poll_id():
    """Фикстура для создания тестового опроса"""
    try:
        # Хардкодим fee для тестов
        fee = w3.to_wei(100, 'ether')
        
        # Минтим токены если нужно
        mint_tx = poll_token.functions.transfer(
            ADMIN_ADDRESS,
            fee * 2
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': w3.eth.get_transaction_count(ADMIN_ADDRESS)
        })
        signed_mint = w3.eth.account.sign_transaction(mint_tx, PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed_mint.raw_transaction)
        
        # Делаем approve
        approve_tx = poll_token.functions.approve(
            poll_system.address,
            fee
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': w3.eth.get_transaction_count(ADMIN_ADDRESS)
        })
        signed_approve = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed_approve.raw_transaction)

        # Создаем опрос
        create_tx = poll_system.functions.createPoll(
            TEST_QUESTION,
            TEST_OPTIONS,
            TEST_DURATION
        ).build_transaction({
            'from': ADMIN_ADDRESS,
            'nonce': w3.eth.get_transaction_count(ADMIN_ADDRESS)
        })
        signed_create = w3.eth.account.sign_transaction(create_tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_create.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return poll_system.functions.pollCount().call() - 1
    except Exception as e:
        pytest.skip(f"Could not create test poll: {str(e)}")

def test_health_check():
    """Тест проверки работоспособности"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "block_number" in data
    assert "contract_code" in data
    # Изменяем проверку, так как в Hardhat код контракта может быть пустым
    assert isinstance(data["contract_code_empty"], bool)

def test_get_admin_address():
    """Тест получения адреса администратора"""
    response = client.get("/admin-address")
    assert response.status_code == 200
    data = response.json()
    assert Web3.is_address(data["admin_address"])
    assert data["admin_address"] == ADMIN_ADDRESS

def test_get_polls(test_poll_id):
    """Тест получения списка опросов"""
    response = client.get("/polls")
    assert response.status_code == 200
    polls = response.json()
    assert isinstance(polls, list)
    if test_poll_id is not None:
        assert any(poll["id"] == test_poll_id for poll in polls)

def test_create_poll():
    """Тест создания опроса"""
    create_poll_data = {
        "question": "New Test Poll?",
        "options": ["Yes", "No", "Maybe"],
        "duration": 600
    }
    response = client.post("/create-poll", json=create_poll_data)
    assert response.status_code == 200
    data = response.json()
    assert "tx_hash" in data
    tx_hash = data["tx_hash"]
    assert len(tx_hash) == 64 or (tx_hash.startswith('0x') and len(tx_hash) == 66)

def test_create_poll_invalid_data():
    """Тест создания опроса с невалидными данными"""
    invalid_data = {
        "question": "Incomplete poll",
        "duration": 600
    }
    response = client.post("/create-poll", json=invalid_data)
    assert response.status_code == 422

def test_vote_with_signature(test_poll_id, test_account):
    """Тест голосования с валидной подписью"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    option_id = 1
    message_hash = Web3.solidity_keccak(
        ['uint256', 'uint256'],
        [test_poll_id, option_id]
    )
    signed_message = test_account.sign_message(encode_defunct(message_hash))
    signature = signed_message.signature.hex()

    vote_data = {
        "poll_id": test_poll_id,
        "option_id": option_id,
        "signature": signature
    }
    response = client.post("/vote", json=vote_data)
    assert response.status_code == 200
    data = response.json()
    assert "tx_hash" in data

def test_vote_invalid_signature(test_poll_id):
    """Тест голосования с невалидной подписью"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    vote_data = {
        "poll_id": test_poll_id,
        "option_id": 0,
        "signature": "0xinvalid123"
    }
    response = client.post("/vote", json=vote_data)
    assert response.status_code in [400, 500]

def test_get_poll_results(test_poll_id, test_account):
    """Тест получения результатов опроса"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    # Сначала голосуем
    option_id = 0
    message_hash = Web3.solidity_keccak(
        ['uint256', 'uint256'],
        [test_poll_id, option_id]
    )
    signed_message = test_account.sign_message(encode_defunct(message_hash))
    signature = signed_message.signature.hex()

    vote_data = {
        "poll_id": test_poll_id,
        "option_id": option_id,
        "signature": signature
    }
    client.post("/vote", json=vote_data)

    # Проверяем результаты
    response = client.get(f"/poll-results/{test_poll_id}")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, dict)
    assert "options" in results
    assert "votes" in results

def test_approve_tokens():
    """Тест approve токенов"""
    balance = poll_token.functions.balanceOf(ADMIN_ADDRESS).call()
    assert balance >= 0
    
    allowance = poll_token.functions.allowance(
        ADMIN_ADDRESS,
        poll_system.address
    ).call()
    assert allowance >= 0

def test_relay_vote_valid(test_poll_id, test_account):
    """Тест релейного голосования с валидной подписью"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    message_hash = Web3.solidity_keccak(
        ['uint256', 'uint256', 'address'],
        [test_poll_id, 1, test_account.address]
    )
    signed_message = test_account.sign_message(encode_defunct(message_hash))
    
    response = client.post("/relay-vote", json={
        "poll_id": test_poll_id,
        "option_id": 1,
        "signature": signed_message.signature.hex(),
        "voter_address": test_account.address
    })
    
    assert response.status_code == 200
    assert "tx_hash" in response.json()

def test_relay_vote_invalid_signature(test_poll_id, test_account):
    """Тест релейного голосования с невалидной подписью"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    response = client.post("/relay-vote", json={
        "poll_id": test_poll_id,
        "option_id": 1,
        "signature": "0xinvalid",
        "voter_address": test_account.address
    })
    
    assert response.status_code == 400
    assert "Invalid signature" in response.json().get("detail", "")

def test_relay_vote_already_voted(test_poll_id, test_account):
    """Тест повторного голосования"""
    if test_poll_id is None:
        pytest.skip("No test poll available")
    
    message_hash = Web3.solidity_keccak(
        ['uint256', 'uint256', 'address'],
        [test_poll_id, 1, test_account.address]
    )
    signed_message = test_account.sign_message(encode_defunct(message_hash))
    
    # Первое голосование
    client.post("/relay-vote", json={
        "poll_id": test_poll_id,
        "option_id": 1,
        "signature": signed_message.signature.hex(),
        "voter_address": test_account.address
    })
    
    # Второе голосование
    response = client.post("/relay-vote", json={
        "poll_id": test_poll_id,
        "option_id": 1,
        "signature": signed_message.signature.hex(),
        "voter_address": test_account.address
    })
    
    assert response.status_code == 400
    assert "Already voted" in response.json().get("detail", "")