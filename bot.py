from jwt import encode as jwt_encode
import time
import requests
import base64
import os
import yaml
import json
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
)

load_dotenv(override=True)

APP_ID = os.environ.get("APP_ID")
INSTALLATION_ID = os.environ.get("INSTALLATION_ID")
PRIVATE_KEY_PATH = os.environ.get("PRIVATE_KEY_PATH")

if not PRIVATE_KEY_PATH:
    raise ValueError("Configuration error: PRIVATE_KEY_PATH is not set.")

OWNER = "chiyu-li-appier"
REPO_READ = "mock-heqa"
REPO_WRITE = "mock-eam-api"
FILE_PATH = "eam-dev.yml"
USERS_DB = "users.json"
MOCK_API_URL = "http://127.0.0.1:5000/create_user"


def get_existing_users(db_file):
    if not os.path.exists(db_file):
        return set()

    with open(db_file, "r") as f:
        users = set()
        for line in f:
            try:
                users.add(json.loads(line)["email"])
            except json.JSONDecodeError:
                logging.warning(f"Could not decode line: {line}")
        return users


logging.info("Step 1: Generating JWT...")
try:
    with open(PRIVATE_KEY_PATH, "r") as key_file:
        PRIVATE_KEY = key_file.read()
        jwt_token = jwt_encode(
            {"iat": int(time.time()), "exp": int(time.time()) + 540, "iss": APP_ID},
            PRIVATE_KEY,
            algorithm="RS256",
        )
        logging.info("JWT generated.")
except Exception as e:
    logging.exception(f"Error generating JWT: {e}")

logging.info("Step 2: Getting Installation Access Token...")
resp = requests.post(
    f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens",
    headers={
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    },
)
resp.raise_for_status()
token = resp.json()["token"]
logging.info("Access Token received.")

logging.info(f"Step 3: Reading {FILE_PATH} from repo {OWNER}/{REPO_READ}...")
file_resp = requests.get(
    f"https://api.github.com/repos/{OWNER}/{REPO_READ}/contents/{FILE_PATH}",
    headers={"Authorization": f"token {token}"},
)
file_resp.raise_for_status()
file_json = file_resp.json()

content = base64.b64decode(file_json["content"]).decode("utf-8")
logging.info(f"Successfully read file content.")

logging.info("Step 4: Processing users...")
try:
    data = yaml.safe_load(content)
    members = data.get("members", [])
except yaml.YAMLError as e:
    logging.error(f"Error parsing YAML file: {e}")
    members = []

if members:
    existing_users = get_existing_users(USERS_DB)
    logging.info(f"Found {len(existing_users)} existing users in {USERS_DB}.")

    for member in members:
        email = f"{member}@appier.com"
        if email in existing_users:
            logging.info(f"User '{email}' already exists. Skipping.")
        else:
            logging.info(f"User '{email}' not found. Creating account via mock API...")
            try:
                response = requests.get(MOCK_API_URL, params={"email": email})
                response.raise_for_status()
                new_user = response.json()
                logging.info(
                    f"Successfully created user: {new_user['email']} with API key: {new_user['api_key']}"
                )
            except requests.exceptions.RequestException as e:
                logging.error(f"Error creating user '{email}': {e}")
else:
    logging.info("No members found in the YAML file. Nothing to do.")

logging.info("Bot script finished.")
