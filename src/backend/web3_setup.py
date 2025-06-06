import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

from contract_abi import POLL_SYSTEM_ABI, ERC20_ABI, DEPLOY_INFO

load_dotenv()

# Настройки из .env
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
SYSTEM_ADDRESS = os.getenv("CONTRACT_ADDRESS") or DEPLOY_INFO["pollSystemAddress"]
TOKEN_ADDRESS = os.getenv("POLL_TOKEN_ADDRESS") or DEPLOY_INFO["pollTokenAddress"]


w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)
ADMIN = account.address


poll_system = w3.eth.contract(address=SYSTEM_ADDRESS, abi=POLL_SYSTEM_ABI)
poll_token = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_ABI)

print(f"✅ Connected as: {ADMIN}")
print(f"📦 System Contract: {SYSTEM_ADDRESS}")
print(f"💰 Token Contract: {TOKEN_ADDRESS}")