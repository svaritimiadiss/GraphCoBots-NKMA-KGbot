"""
POST
store bot event data: http://analytics.dev.botproxyurl.com/api/bot_event_data
headers:
Content-Type: application/json
assistant-id: 20240606-104308-local-commission
body:
 {
 "145205": {
        "sender_id": "front-webchat-PZC-1728545835",
        "data": {
            "event": "bot",
            "timestamp": 1728546138.8764968,
            "metadata": {
                "model_id": "e7aeed34d3234ff9bed2f67d82a5c3f0",
                "assistant_id": "20240606-104308-local-commission"
            },
            "text": "\u0391\u03cd\u03c1\u03b9\u03bf \u03c3\u03c4\u03b7 \u039c\u03c5\u03c1\u03c4\u03b9\u03ac, \u03b8\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03bc\u03af\u03b1 \u03b7\u03bb\u03b9\u03cc\u03bb\u03bf\u03c5\u03c3\u03c4\u03b7 \u03bc\u03ad\u03c1\u03b1 \u2600\ufe0f, \u03ba\u03b1\u03c4\u03ac\u03bb\u03bb\u03b7\u03bb\u03b7 \u03b3\u03b9\u03b1 \u03bd\u03b1 \u03bc\u03b1\u03c2 \u03b5\u03c0\u03b9\u03c3\u03ba\u03b5\u03c6\u03b8\u03b5\u03af\u03c4\u03b5!",
            "data": {
                "elements": null,
                "quick_replies": null,
                "buttons": null,
                "attachment": null,
                "image": null,
                "custom": null
            }
        }
    },
    "145206": {
        "sender_id": "front-webchat-PZC-1728545835",
        "data": {
            "event": "bot",
            "timestamp": 1728546138.8764968,
            "metadata": {
                "model_id": "e7aeed34d3234ff9bed2f67d82a5c3f0",
                "assistant_id": "20240606-104308-local-commission"
            },
            "text": "\u0391\u03cd\u03c1\u03b9\u03bf \u03c3\u03c4\u03b7 \u039c\u03c5\u03c1\u03c4\u03b9\u03ac, \u03b8\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03bc\u03af\u03b1 \u03b7\u03bb\u03b9\u03cc\u03bb\u03bf\u03c5\u03c3\u03c4\u03b7 \u03bc\u03ad\u03c1\u03b1 \u2600\ufe0f, \u03ba\u03b1\u03c4\u03ac\u03bb\u03bb\u03b7\u03bb\u03b7 \u03b3\u03b9\u03b1 \u03bd\u03b1 \u03bc\u03b1\u03c2 \u03b5\u03c0\u03b9\u03c3\u03ba\u03b5\u03c6\u03b8\u03b5\u03af\u03c4\u03b5!",
            "data": {
                "elements": null,
                "quick_replies": null,
                "buttons": null,
                "attachment": null,
                "image": null,
                "custom": null
            }
        }
    }
}

POST
Store Graph Data: http://analytics.dev.botproxyurl.com/api/graph_data
headers:
Content-Type: application/json
body:
{
      "graph_type_id": "gt3116546",
      "graph_type_name": "graphType",
      "bot_metadata": {
        "model_id": "e7aeed34d32",
        "assistant_id": "exhibition-bot-kazantzakis"
      }
}

GET
Last bot event id: http://analytics.dev.botproxyurl.com/api/last_event_id
headers:
Content-Type: application/json

GET
Show Graph Data by assistant_id: http://analytics.dev.botproxyurl.com/api/graph_data/{assistant_id}
headers:
Content-Type: application/json
"""

'''
Έτσι θα είναι το format του store bot event data
{
  "14538": { ... },
  "14539": { ... },
  "14540": { ... }
}
'''

import psycopg2
import json
import requests
from dotenv import load_dotenv
import os
import yaml
import logging
from pathlib import Path


# Get the root directory (assuming your script is in a subfolder)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # Adjust based on depth

# Load the .env file from the root directory
dotenv_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path)

# ------------------------------------------------------------------------------
# Configure Logging
# ------------------------------------------------------------------------------
# For local use
# LOG_DIR = "/usr/src/app/logs"

APP_PATH = os.getenv("APP_PATH", "/app")
LOG_DIR = f"{APP_PATH}/logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)


# ------------------------------------------------------------------------------
# Load YAML Database Config (endpoints.yml)
# ------------------------------------------------------------------------------
# For local use
# with open("/usr/src/app/endpoints.yml", 'r') as file:
#     data = yaml.safe_load(file)

# # Για local testing
# db_host = data['tracker_store']['url']
# db_name = data['tracker_store']['db']  # e.g. "exhibition_kazantzakis"
# db_user = data['tracker_store']['username']
# db_password = data['tracker_store']['password']
# db_port = 5432

# Retrieve tracker_store details from environment variables
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_DATABASE')
db_user = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')
# Provide a default port of 5432 if DB_PORT is not set
db_port = int(os.getenv('DB_PORT', 5432))

logging.info(f"Endpoints data loaded. Using DB: {db_name}")

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
POST_URL = os.getenv("BOT_EVENT_DATA_POST_URL")
LAST_ID_ENDPOINT = os.getenv("BOT_EVENT_DATA_LAST_ID_ENDPOINT")

# ------------------------------------------------------------------------------
# Data Directory
# ------------------------------------------------------------------------------
# For local use
# data_directory = "/usr/src/app/data"
data_directory = f"{APP_PATH}/data"
os.makedirs(data_directory, exist_ok=True)
new_data_file_path = os.path.join(data_directory, "new_data.json")

# ------------------------------------------------------------------------------
# Database Connection
# ------------------------------------------------------------------------------
try:
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cur = conn.cursor()
    logging.info("Connected to the database successfully.")
except Exception as e:
    logging.error(f"Failed to connect to the database: {e}")
    raise SystemExit(e)

# ------------------------------------------------------------------------------
# 1) Retrieve the latest processed ID from the external API
# ------------------------------------------------------------------------------
try:
    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }
    response = requests.get(LAST_ID_ENDPOINT, headers=headers)
    logging.info(f"Response from GET {LAST_ID_ENDPOINT}: {response.text}")

    if response.status_code == 200:
        last_id_data = response.json()
        remote_latest_id = last_id_data.get("last_event_id", 0)
        logging.info(f"Retrieved latest processed ID from API: {remote_latest_id}")
    else:
        logging.info(f"Failed to retrieve last processed ID. "
                     f"Status code: {response.status_code}, Response: {response.text}")
        remote_latest_id = 0
except requests.RequestException as e:
    logging.info(f"Error during GET {LAST_ID_ENDPOINT}: {e}")
    remote_latest_id = 0

# ------------------------------------------------------------------------------
# 2) Query only new entries from the local DB (id > remote_latest_id)
# ------------------------------------------------------------------------------
query = "SELECT id, sender_id, data FROM events WHERE id > %s"
cur.execute(query, (remote_latest_id,))
rows = cur.fetchall()
logging.info(f"Fetched {len(rows)} new rows (id > {remote_latest_id}).")

# Prepare a dictionary to hold new data (keyed by string record_id)
new_data = {}
max_id = remote_latest_id

# ------------------------------------------------------------------------------
# Process each row
# ------------------------------------------------------------------------------
for row in rows:
    record_id = row[0]  # integer ID
    sender_id = row[1]
    data_str = row[2]  # JSON string from DB

    try:
        parsed_data = json.loads(data_str)
        new_data[str(record_id)] = {
            "sender_id": sender_id,
            "data": parsed_data
        }
        if record_id > max_id:
            max_id = record_id
    except json.JSONDecodeError:
        logging.info(f"Error decoding JSON for id {record_id}: {data_str}")
        continue

# ------------------------------------------------------------------------------
# If there's new data, store & post it
# ------------------------------------------------------------------------------
if new_data:
    # Just save the raw dictionary (keys = record_ids)
    # Example final JSON structure:
    # {
    #   "14538": { ... },
    #   "14539": { ... }
    # }
    with open(new_data_file_path, "w") as f:
        json.dump(new_data, f, indent=4)
    logging.info(f"New data saved to {new_data_file_path}")


    def post_new_data(file_path):
        """Reads and posts JSON data to POST_URL, sending assistant_botid in the header."""
        try:
            with open(file_path, "r") as f:
                data_for_post = json.load(f)
        except Exception as e:
            logging.info(f"Failed to load JSON from {file_path}: {e}")
            return

        if not data_for_post:
            logging.info("No new data to post. The JSON file is empty.")
            return

        logging.info(f"Posting new data to {POST_URL}")
        headers = {
            'Content-Type': 'application/json',
            'assistant-botid': 'exhibition-bot-kazantzakis'
        }

        try:
            response = requests.post(POST_URL, json=data_for_post, headers=headers)
            logging.info("response_post: ", response)
        except requests.RequestException as e:
            logging.info(f"Failed to reach {POST_URL}: {e}")
            return

        if response.status_code == 200:
            logging.info("New data posted successfully.")
            try:
                response_data = response.json()
                logging.info("response_data: ", response_data)
                if "results" in response_data:
                    error_detected = False
                    latest_bot_event_data_id = 0

                    for item in response_data["results"]:
                        status = item.get("status", "")
                        bot_event_data_id = item.get("bot_event_data_id", 0)
                        if bot_event_data_id > latest_bot_event_data_id:
                            latest_bot_event_data_id = bot_event_data_id

                        if status.lower() == "error":
                            error_detected = True
                            logging.info(f"Error for bot_event_data_id {bot_event_data_id}: "
                                         f"{item.get('message')}")

                    if error_detected:
                        logging.info("One or more errors detected; checking for missing data...")
                        if latest_bot_event_data_id < max_id:
                            logging.info(
                                f"Local max_id: {max_id}, response max_id with error: {latest_bot_event_data_id}")
                            fetch_and_post_missing_data(latest_bot_event_data_id, max_id)
                        else:
                            logging.info("No missing data to post despite the error.")
                    else:
                        logging.info("No critical errors in POST results.")
                else:
                    logging.info("No 'results' field found in the POST response JSON.")
            except json.JSONDecodeError:
                logging.info(f"Failed to parse the POST response: {response.text}")
        else:
            logging.info(f"Failed to post new data. Status code: {response.status_code}, "
                         f"Response: {response.text}")


    def fetch_and_post_missing_data(start_id, end_id):
        """Fetch missing data between start_id+1 and end_id, then re-post with assistant_botid as a header."""
        query_missing = "SELECT id, sender_id, data FROM events WHERE id > %s AND id <= %s"
        cur.execute(query_missing, (start_id, end_id))
        rows_missing = cur.fetchall()
        if not rows_missing:
            logging.info("No missing data found to post.")
            return

        missing_data = {}
        for row in rows_missing:
            record_id = row[0]
            sender_id = row[1]
            data_str = row[2]
            try:
                parsed_data = json.loads(data_str)
                missing_data[str(record_id)] = {
                    "sender_id": sender_id,
                    "data": parsed_data
                }
            except json.JSONDecodeError:
                logging.info(f"Error decoding JSON for id {record_id}: {data_str}")
                continue

        headers = {
            'Content-Type': 'application/json',
            'assistant-botid': 'exhibition-bot-kazantzakis'
        }

        logging.info(f"Posting missing data for IDs between {start_id} and {end_id}...")
        try:
            response = requests.post(POST_URL, json=missing_data, headers=headers)
            if response.status_code == 200:
                logging.info("Missing data posted successfully.")
            else:
                logging.info(f"Failed to post missing data. Status code: {response.status_code}, "
                             f"Response: {response.text}")
        except requests.RequestException as e:
            logging.info(f"Failed to reach {POST_URL} while posting missing data: {e}")


    # Finally, post the new data
    post_new_data(new_data_file_path)

else:
    logging.info("No new data to save or post.")

# ------------------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------------------
cur.close()
conn.close()
logging.info("Database connection closed.")
