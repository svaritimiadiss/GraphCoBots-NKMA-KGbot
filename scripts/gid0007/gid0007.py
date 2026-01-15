#!/usr/bin/env python3
"""
Hourly Popular-Intents Script with Sync Check

 - We query the analytics server (ANALYTICS_GET_URL) to see the last posted end_datetime.
 - If none found, we default to earliest event in our DB.
 - Then we create 1-hour intervals from that last posted time up to the current hour boundary.
 - For each interval, we query the DB for user events (type_name='user'), grouped by intent_name.
 - POST those results in JSON format to ANALYTICS_POST_URL (200 or 201 = success).
 - We skip any intervals already posted or beyond the current hour.

Environment variables (via .env or directly in the environment):
  - ANALYTICS_GET_URL
  - ANALYTICS_POST_URL
  - DB credentials (or loaded from endpoints.yml)
"""

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

# ------------------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Analytics Endpoints
# ------------------------------------------------------------------------------
ANALYTICS_GET_URL = os.getenv('TRIGGERED_INTENTS_GET_URL')
ANALYTICS_POST_URL = os.getenv('TRIGGERED_INTENTS_POST_URL')


# ------------------------------------------------------------------------------
# DB Credentials
# ------------------------------------------------------------------------------
def load_db_credentials(endpoints_yml_path):
    """
    Load DB credentials from endpoints.yml or environment variables.
    Adjust as needed based on your real endpoints.yml structure.
    """
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


# ------------------------------------------------------------------------------
# Parsing / Utilities
# ------------------------------------------------------------------------------
def parse_iso_to_utc_dt(iso_str):
    """
    Convert e.g. '2025-02-17T00:00:00Z' -> datetime(2025,2,17,0,0,0,tzinfo=UTC).
    Return None if invalid or iso_str is None.
    """
    if not iso_str:
        return None
    try:
        # Replace trailing 'Z' with '+00:00' so fromisoformat can parse
        if iso_str.endswith("Z"):
            iso_str = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(iso_str)
    except ValueError as e:
        logging.error("Failed to parse ISO datetime string '%s': %s", iso_str, e)
        return None


def snap_to_hour(dt_utc):
    """
    Given a UTC datetime, truncate to the top of the hour (00 minutes, 00 seconds).
    """
    return dt_utc.replace(minute=0, second=0, microsecond=0)


def generate_hour_intervals(start_hour, end_hour):
    """
    Generate a list of [start_hour -> next_hour) intervals, hour by hour,
    from start_hour up to (but not including) end_hour.
    """
    intervals = []
    current_start = start_hour
    while current_start < end_hour:
        next_hour = current_start + timedelta(hours=1)
        if next_hour > end_hour:
            next_hour = end_hour
        intervals.append((current_start, next_hour))
        current_start = next_hour
    return intervals


# ------------------------------------------------------------------------------
# GET the Server's Last Known End Datetime
# ------------------------------------------------------------------------------
def get_server_latest_end_dt(bot_id):
    """
    Query ANALYTICS_GET_URL for the server's last recorded end_datetime for this bot.
    Return a UTC datetime or None if nothing is found or error occurs.
    Example JSON response:
      {
         "data": {
            "end_datetime": "2025-02-17T13:00:00Z"
         }
      }
    """
    if not ANALYTICS_GET_URL:
        logging.warning("ANALYTICS_GET_URL not set. Can't sync with server.")
        return None

    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }

    try:
        resp = requests.get(ANALYTICS_GET_URL, headers=headers)
        logging.info("GET status: %d, response text: %s", resp.status_code, resp.text)
        if resp.status_code == 200:
            resp_json = resp.json()
            iso_str = resp_json.get("end_datetime")
            return parse_iso_to_utc_dt(iso_str)
        else:
            logging.warning("Server GET returned status %d, no valid data found.", resp.status_code)
            return None
    except Exception as e:
        logging.error("Error in GET request: %s", e)
        return None


# ------------------------------------------------------------------------------
# Earliest DB Timestamp
# ------------------------------------------------------------------------------
def earliest_db_timestamp_utc(db_creds):
    """
    Return the earliest user-event timestamp found in the events table as a UTC datetime.
    We specifically look at (data::json->>'timestamp') if that's how Rasa stores it.

    If no rows or error, return None.
    """
    db_host, db_name, db_user, db_password, db_port = db_creds
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        cursor = conn.cursor()
        # Filter only user events (type_name='user'), just in case
        # We cast the JSON string to double precision and take MIN.
        query = """
        SELECT MIN((data::json->>'timestamp')::double precision)
        FROM events
        WHERE type_name = 'user';
        """
        cursor.execute(query)
        row = cursor.fetchone()
        if not row or row[0] is None:
            logging.warning("No user events found in DB (MIN timestamp is null).")
            return None
        min_ts = float(row[0])
        earliest_dt = datetime.fromtimestamp(min_ts, tz=timezone.utc)
        return earliest_dt
    except Exception as e:
        logging.error("Error retrieving earliest DB timestamp: %s", e)
        return None
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------
# Query the Database for Intent Counts within [start_dt, end_dt)
# ------------------------------------------------------------------------------
def query_intent_counts(db_creds, start_dt, end_dt):
    """
    Query for all user events within [start_dt, end_dt), grouped by intent_name.

    Returns a list of dicts: [{ "intent_name": "...", "count": 5}, ...]
    """
    db_host, db_name, db_user, db_password, db_port = db_creds
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        cursor = conn.cursor()

        query = """
        SELECT intent_name, COUNT(*) AS total
        FROM events
        WHERE type_name = 'user'
          AND (data::json->>'timestamp')::double precision >= %s
          AND (data::json->>'timestamp')::double precision < %s
        GROUP BY intent_name
        ORDER BY total DESC;
        """

        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()

        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()

        intent_counts = []
        for (intent_name, total) in rows:
            # Convert None (NULL) to a placeholder
            intent_name = intent_name if intent_name else "unknown_intent"
            intent_counts.append({"intent_name": intent_name, "count": total})

        logging.info("Intent count [%s->%s): %d rows",
                     start_dt.isoformat(), end_dt.isoformat(), len(intent_counts))

        return intent_counts
    except Exception as e:
        logging.error("Error querying intent counts: %s", e)
        return []
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------
# Post the Interval Data
# ------------------------------------------------------------------------------
def post_interval_data(bot_id, start_dt, end_dt, intent_counts):
    """
    POST the hourly intent counts to ANALYTICS_POST_URL in the required format.

    Example body:
      {
        "graph_type_id": "gid0008",
        "start_datetime": "2025-02-17T00:00:00Z",
        "end_datetime":   "2025-02-17T01:00:00Z",
        "intents_count": [
          {"intent_name": "welcome", "count": 5},
          ...
        ]
      }
    Accepts 200 or 201 as success.
    """
    if not ANALYTICS_POST_URL:
        logging.warning("ANALYTICS_POST_URL not set. Skipping POST.")
        return False

    headers = {
        "Content-Type": "application/json",
        "assistant-botid": 'exhibition-bot-kazantzakis'
    }

    body = {
        "graph_type_id": "gid0007",  # or whatever ID you prefer
        "start_datetime": start_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_datetime": end_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "triggered_intents_count": intent_counts
    }

    logging.info("Posting interval data: %s", body)
    try:
        resp = requests.post(ANALYTICS_POST_URL, headers=headers, json=body)
        logging.info("POST status: %d, response: %s", resp.status_code, resp.text)
        if resp.status_code in [200, 201]:
            return True
        else:
            logging.error("POST failed with status %d", resp.status_code)
            return False
    except Exception as e:
        logging.error("Error in POST request: %s", e)
        return False


# ------------------------------------------------------------------------------
# Main Sync Logic
# ------------------------------------------------------------------------------
def fill_missing_hourly_intervals(db_creds):
    """
    1) Find the server's last posted end_datetime.
    2) If not found, default to earliest user-event timestamp in DB.
    3) Snap that time to the hour.
    4) Snap current time to the hour.
    5) Generate [server_end_dt -> current_hour) intervals, step=1 hour.
    6) For each, query DB -> get intent_counts -> POST to server -> stop if any fails.
    """
    db_host, db_name, db_user, db_password, db_port = db_creds

    # 1) Attempt to get last posted hour from server
    server_end_dt = get_server_latest_end_dt(db_name)
    if not server_end_dt:
        # 2) If server has no data, use earliest user-event in DB
        earliest_dt = earliest_db_timestamp_utc(db_creds)
        if earliest_dt:
            server_end_dt = earliest_dt
            logging.info("Defaulting server_end_dt to earliest DB timestamp: %s", server_end_dt)
        else:
            logging.warning("No user events in DB, nothing to post. Exiting.")
            return

    # 3) Snap that to the top of the hour
    start_hour = snap_to_hour(server_end_dt)

    # 4) Snap current time (UTC) to the top of the hour
    now_utc = datetime.now(timezone.utc)
    current_hour_utc = snap_to_hour(now_utc)

    if start_hour >= current_hour_utc:
        logging.info("Server is up-to-date (start_hour=%s >= current_hour=%s)", start_hour, current_hour_utc)
        print("No missing intervals to post.")
        return

    # 5) Generate 1-hour intervals
    intervals = generate_hour_intervals(start_hour, current_hour_utc)
    logging.info("We have %d missing hourly intervals to sync.", len(intervals))

    # 6) For each interval, query and post
    for (interval_start, interval_end) in intervals:
        intent_counts = query_intent_counts(db_creds, interval_start, interval_end)
        success = post_interval_data(db_name, interval_start, interval_end, intent_counts)
        if not success:
            logging.error("Post failed for [%s -> %s), stopping sync.", interval_start, interval_end)
            break
        else:
            logging.info("Successfully posted [%s -> %s).", interval_start, interval_end)
            print(f"Posted interval: [{interval_start.isoformat()} -> {interval_end.isoformat()})")

        time.sleep(2)  # optional delay to avoid hammering the endpoint


def main():
    logging.info("=== Starting Hourly Popular-Intents Sync ===")
    db_creds = load_db_credentials("/usr/src/app/endpoints.yml")
    fill_missing_hourly_intervals(db_creds)
    logging.info("=== Finished Hourly Popular-Intents Sync ===")


if __name__ == "__main__":
    main()
