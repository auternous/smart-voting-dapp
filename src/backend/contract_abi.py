import os
import json

BASE_DIR = os.path.dirname(__file__)
DEPLOYMENTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../deployments"))

with open(os.path.join(DEPLOYMENTS_DIR, "poll_system_abi.json")) as f:
    POLL_SYSTEM_ABI = json.load(f)

with open(os.path.join(DEPLOYMENTS_DIR, "poll_token_abi.json")) as f:
    ERC20_ABI = json.load(f)

with open(os.path.join(DEPLOYMENTS_DIR, "deploy.json")) as f:
    DEPLOY_INFO = json.load(f)