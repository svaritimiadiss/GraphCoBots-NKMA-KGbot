#!/usr/bin/env python3

import os
import requests
import logging
import psycopg2
from datetime import datetime, timezone, timedelta
import yaml
import time
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

logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# ANALYTICS_GET_URL = "https://analytics.dev.botproxyurl.com/api/daily_active_users/last"
# ANALYTICS_POST_URL = "https://analytics.dev.botproxyurl.com/api/store_daily_active_users"
ANALYTICS_GET_URL = os.getenv('DAILY_ACTIVE_USERS_GET_URL')
ANALYTICS_POST_URL = os.getenv('DAILY_ACTIVE_USERS_POST_URL')


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


def get_last_posted_end_datetime(db_name):
    headers = {
        "Content-Type": "application/json",
        "assistant-botid": 'exhibition-bot-kazantzakis'
    }
    try:
        resp = requests.get(ANALYTICS_GET_URL, headers=headers)
        resp.raise_for_status()

        response_json = resp.json()
        # The last record data is nested under "data"
        record_data = response_json.get("data", {})
        end_datetime_str = record_data.get("end_datetime")

        if end_datetime_str is None:
            logging.info("No end_datetime found in last record. Possibly no data posted yet.")
            return None

        # Convert "2025-02-14T16:00:00.000000Z" => Python datetime
        # If it ends with Z, replace with +00:00 so fromisoformat() works
        if end_datetime_str.endswith("Z"):
            end_datetime_str = end_datetime_str.replace("Z", "+00:00")

        last_end_dt = datetime.fromisoformat(end_datetime_str)
        logging.info("Last posted end_datetime is %s (UTC)", last_end_dt.isoformat())
        return last_end_dt

    except requests.HTTPError as e:
        logging.error("GET request failed: %s", e)
        return None
    except Exception as e:
        logging.error("Error parsing last record data: %s", e)
        return None


def query_user_count(db_creds, start_dt, end_dt):
    """
    Query the DB for distinct sender_ids from start_dt to end_dt (UTC).
    """
    db_host, db_name, db_user, db_password, db_port = db_creds

    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
    cursor = conn.cursor()

    query = """
    SELECT COUNT(DISTINCT sender_id) AS user_count
    FROM events
    WHERE (data::json->>'timestamp') IS NOT NULL
      AND (data::json->>'timestamp')::double precision >= %s
      AND (data::json->>'timestamp')::double precision < %s;
    """

    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

    cursor.execute(query, (start_ts, end_ts))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    user_count = row[0] if row else 0
    logging.info("Query from %s to %s => user_count=%d", start_dt, end_dt, user_count)
    return user_count


def post_interval_data(start_dt, end_dt, user_count, db_name):
    """
    POST the data for one hour block to the analytics endpoint in the required format.
    Example desired body:
      {
        "graph_type_id": "gid0001",
        "start_datetime": "2025-02-14T09:00:00Z",
        "end_datetime":   "2025-02-14T10:00:00Z",
        "users_count": 5
      }
    """
    headers = {
        "Content-Type": "application/json",
        "assistant-botid": 'exhibition-bot-kazantzakis'
    }

    body = {
        "graph_type_id": "gid0001",
        "start_datetime": start_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_datetime": end_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "users_count": user_count
    }
    logging.info("POSTing interval: %s", body)

    resp = requests.post(ANALYTICS_POST_URL, headers=headers, json=body)
    try:
        resp.raise_for_status()
        logging.info("POST success. Response: %s", resp.text)
    except Exception as e:
        logging.error("POST to %s failed: %s", ANALYTICS_POST_URL, e)


def fill_missing_intervals(db_creds):
    db_host, db_name, db_user, db_password, db_port = db_creds

    last_end_dt = get_last_posted_end_datetime(db_name)
    if not last_end_dt:
        logging.info("No last_end_dt found. Starting from 24h ago.")
        last_end_dt = datetime.now(timezone.utc) - timedelta(hours=24)

    last_end_dt = last_end_dt.replace(minute=0, second=0, microsecond=0)
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = now_utc.replace(minute=0, second=0, microsecond=0)

    start_dt = last_end_dt

    while start_dt < current_hour_utc:
        end_dt = start_dt + timedelta(hours=1)
        if end_dt > current_hour_utc:
            break

        user_count = query_user_count(db_creds, start_dt, end_dt)
        post_interval_data(start_dt, end_dt, user_count, db_name)

        # Sleep 2 seconds after each post to avoid hammering the endpoint
        time.sleep(2)

        start_dt = end_dt


def main():
    logging.info("=== Starting missing-intervals check ===")
    # db_creds = load_db_credentials("/usr/src/app/endpoints.yml")
    # db_creds = load_db_credentials("C:/Users/giorg/PycharmProjects/hotel-bot/endpoints.yml")
    db_creds = load_db_credentials("/app/endpoints.yml")
    fill_missing_intervals(db_creds)
    logging.info("=== Finished missing-intervals check ===")


if __name__ == "__main__":
    main()
