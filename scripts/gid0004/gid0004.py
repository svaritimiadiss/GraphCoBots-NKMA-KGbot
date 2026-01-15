"""
Number of Conversations: Weekly number of conversations.
"""

import os
import json
import yaml
import psycopg2
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo  # For timezone conversions
from dotenv import load_dotenv
from pathlib import Path

# Get the root directory (assuming your script is in a subfolder)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # Adjust based on depth

# Load the .env file from the root directory
dotenv_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path)

APP_PATH = os.getenv("APP_PATH", "/app")
LOG_DIR = f"{APP_PATH}/logs"
# LOG_DIR = "/usr/src/app/logs"

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")


# Create a custom formatter that converts time to Athens time.
class AthensFormatter(logging.Formatter):
    def converter(self, timestamp):
        # Convert the epoch timestamp to Athens time.
        dt = datetime.fromtimestamp(timestamp, ZoneInfo("Europe/Athens"))
        return dt.timetuple()


# Set up logging using our custom formatter.
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Override the converter for all log formatters so log timestamps are in Athens time.
logging.Formatter.converter = AthensFormatter().converter

ANALYTICS_POST_URL = os.getenv('GRAPH_DATE_POST_URL')

def load_db_credentials(endpoints_yml_path):
    # with open(endpoints_yml_path, 'r') as f:
    #     endpoints_data = yaml.safe_load(f)

    # Retrieve tracker_store details from environment variables
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_DATABASE')
    db_user = os.getenv('DB_USERNAME')
    db_password = os.getenv('DB_PASSWORD')
    # Provide a default port of 5432 if DB_PORT is not set
    db_port = int(os.getenv('DB_PORT', 5432))

    # tracker_store = endpoints_data.get('tracker_store', {})
    # db_host = tracker_store.get('url')
    # db_name = tracker_store.get('db')
    # db_user = tracker_store.get('username')
    # db_password = tracker_store.get('password')
    # db_port = tracker_store.get('port', 5432)

    return db_host, db_name, db_user, db_password, db_port


def count_weekly_conversations(db_host, db_name, db_user, db_password, db_port):
    """
    Connect to Postgres and compute the total unique sender_ids (conversations) from Monday to now.

    Returns a tuple: (week_start_date, weekly_count)
    """
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cursor = conn.cursor()

    query = """
SET TIME ZONE 'Europe/Athens';

SELECT
    DATE_TRUNC('week', NOW())::date AS week_start,
    COUNT(DISTINCT sender_id) AS weekly_conversations
FROM events
WHERE (data::json->>'timestamp') IS NOT NULL
  AND DATE(
        to_timestamp(
            (data::json->>'timestamp')::double precision
        ) AT TIME ZONE 'Europe/Athens'
      ) >= DATE_TRUNC('week', NOW())::date;
    """

    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    logging.info("Fetched weekly conversation count: %s", row)
    return row if row is not None else (None, 0)


if __name__ == "__main__":
    logging.info("Starting the script to compute weekly conversation counts.")

    # 1. Load DB credentials from the endpoints.yml file.
    db_host, db_name, db_user, db_password, db_port = load_db_credentials("/usr/src/app/endpoints.yml")

    # 2. Get the weekly conversation count.
    week_start, weekly_count = count_weekly_conversations(db_host, db_name, db_user, db_password, db_port)

    # 3. Get the current Athens time to label the latest snapshot.
    now_athens = datetime.now(ZoneInfo("Europe/Athens"))
    day_str = now_athens.strftime("%Y-%m-%d")
    time_str = now_athens.strftime("%H:%M:%S")

    # Build the JSON payload.
    graph_data = {
        "week_start": str(week_start),
        "current_day": day_str,
        "current_time": time_str,
        "weekly_conversations": weekly_count
    }

    # 4. Prepare headers and the payload for posting.
    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }

    payload = {
        "graph_type_id": "gid0004",
        "bot_metadata": graph_data,
    }

    # 5. Post the payload to an API endpoint (httpbin.org is used here for testing).
    try:
        logging.info("Posting payload to %s ...", ANALYTICS_POST_URL)
        logging.info("Payload: %s", payload)
        response = requests.post(ANALYTICS_POST_URL, json=payload, headers=headers)
        logging.info("Response status code: %d", response.status_code)
        logging.info("Response text: %s", response.text)
    except Exception as e:
        logging.error("Error when posting to %s: %s", ANALYTICS_POST_URL, e)

    logging.info("Finished computing and posting weekly conversation counts.")
