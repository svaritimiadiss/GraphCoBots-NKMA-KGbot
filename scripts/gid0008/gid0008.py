#!/usr/bin/env python3
"""
Hourly NLU Fallback Script with Sync Check

 - We query the analytics server (TRIGGERED_FALLBACKS_GET_URL) to see the last posted end_datetime.
 - If none found, we default to earliest user-event timestamp in our DB.
 - Then we create 1-hour intervals from that last posted time up to the current hour boundary (UTC).
 - For each interval, we query the DB for user events (type_name='user'), looking specifically for 'nlu_fallback'.
 - POST those results in JSON format to TRIGGERED_FALLBACKS_POST_URL (200 or 201 = success).
 - We skip any intervals already posted or beyond the current hour.
"""

import os
import requests
import logging
import psycopg2
from datetime import datetime, timezone, timedelta
import yaml
import time
import json
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
FALLBACKS_GET_URL = os.getenv('UNRECOGNIZED_MESSAGES_GET_URL')
FALLBACKS_POST_URL = os.getenv('UNRECOGNIZED_MESSAGES_POST_URL')


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

    # tracker_store = endpoints_data.get('tracker_store', {})
    # db_host = tracker_store.get('url')
    # db_name = tracker_store.get('db')
    # db_user = tracker_store.get('username')
    # db_password = tracker_store.get('password')
    # db_port = tracker_store.get('port', 5432)

    # Retrieve tracker_store details from environment variables (or from the .yml)
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_DATABASE')
    db_user = os.getenv('DB_USERNAME')
    db_password = os.getenv('DB_PASSWORD')
    db_port = int(os.getenv('DB_PORT', 5432))

    return db_host, db_name, db_user, db_password, db_port


# ------------------------------------------------------------------------------
# Parsing / Utilities
# ------------------------------------------------------------------------------
def parse_iso_to_utc_dt(iso_str):
    """
    Convert e.g. '2025-02-17T00:00:00Z' -> datetime(2025,2,17,0,0,0, tzinfo=UTC).
    Return None if invalid or iso_str is None.
    """
    if not iso_str:
        return None
    try:
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
    Query FALLBACKS_GET_URL for the server's last recorded end_datetime for this bot.
    Return a UTC datetime or None if nothing is found or error occurs.

    Example JSON response:
      {
        "end_datetime": "2025-02-17T13:00:00Z"
      }
    """
    if not FALLBACKS_GET_URL:
        logging.warning("TRIGGERED_FALLBACKS_GET_URL not set. Can't sync with server.")
        return None

    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }

    try:
        resp = requests.get(FALLBACKS_GET_URL, headers=headers)
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
# Query the Database for NLU Fallbacks within [start_dt, end_dt)
# ------------------------------------------------------------------------------
def query_fallback_data(db_creds, start_dt, end_dt):
    """
    Query for all user events within [start_dt, end_dt), filtering for 'nlu_fallback'.
    Returns (fallback_count, fallback_messages_list)
       fallback_messages_list = [ { "sender_id": "...", "text": "..."} ]
    """
    db_host, db_name, db_user, db_password, db_port = db_creds
    conn = None
    fallback_messages = []

    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

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
        SELECT sender_id, data
        FROM events
        WHERE type_name = 'user'
          AND (data::json->>'timestamp')::double precision >= %s
          AND (data::json->>'timestamp')::double precision < %s
        """
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()

        for (sender_id, raw_data) in rows:
            if not raw_data:
                continue

            try:
                event_json = json.loads(raw_data)
            except Exception:
                continue

            # check parse_data -> intent -> name
            parse_data = event_json.get("parse_data", {})
            intent = parse_data.get("intent", {})
            if intent.get("name") == "nlu_fallback":
                fallback_messages.append({
                    "sender_id": sender_id,
                    "text": event_json.get("text", "")
                })

        logging.info("Found %d fallback events in [%s->%s).",
                     len(fallback_messages),
                     start_dt.isoformat(),
                     end_dt.isoformat())

    except Exception as e:
        logging.error("Error querying fallback data: %s", e)
    finally:
        if conn:
            conn.close()

    return len(fallback_messages), fallback_messages


# ------------------------------------------------------------------------------
# Post the Interval Data
# ------------------------------------------------------------------------------
def post_interval_fallbacks(bot_id, start_dt, end_dt, fallback_count, fallback_list):
    """
    POST the hourly fallback data to FALLBACKS_POST_URL in the required format.

    Example body:
      {
        "graph_type_id": "gid0007",
        "start_datetime": "2025-02-17T00:00:00Z",
        "end_datetime":   "2025-02-17T01:00:00Z",
        "total_fallback_count": 5,
        "fallback_messages": [
          {"sender_id": "...", "text": "..."},
          ...
        ]
      }
    Accept 200 or 201 as success.
    """
    if not FALLBACKS_POST_URL:
        logging.warning("TRIGGERED_FALLBACKS_POST_URL not set. Skipping POST.")
        return False

    headers = {
        "Content-Type": "application/json",
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }

    body = {
        "graph_type_id": "gid0008",
        "start_datetime": start_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_datetime": end_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "total_fallback_count": fallback_count,
        "fallback_messages": fallback_list
    }

    logging.info("Posting fallback interval data: %s", body)
    try:
        resp = requests.post(FALLBACKS_POST_URL, headers=headers, json=body)
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
# Main Sync Logic: Fill Missing Hourly Intervals
# ------------------------------------------------------------------------------
def fill_missing_hourly_intervals(db_creds):
    """
    1) Find the server's last posted end_datetime (FALLBACKS_GET_URL).
    2) If not found, default to earliest user-event timestamp in DB.
    3) Snap that time to the hour.
    4) Snap current time (UTC) to the hour.
    5) Generate [server_end_dt -> current_hour) intervals, step=1 hour.
    6) For each, query DB -> get fallback data -> POST to server -> stop if any fails.
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
        logging.info("Server up-to-date (start_hour=%s >= current_hour=%s)", start_hour, current_hour_utc)
        print("No missing intervals to post.")
        return

    # 5) Generate 1-hour intervals
    intervals = generate_hour_intervals(start_hour, current_hour_utc)
    logging.info("We have %d missing hourly intervals to sync for nlu_fallback.", len(intervals))

    # 6) For each interval, query and post
    for (interval_start, interval_end) in intervals:
        fallback_count, fallback_list = query_fallback_data(db_creds, interval_start, interval_end)
        success = post_interval_fallbacks(db_name, interval_start, interval_end, fallback_count, fallback_list)
        if not success:
            logging.error("Post failed for [%s -> %s), stopping sync.", interval_start, interval_end)
            break
        else:
            logging.info("Successfully posted [%s -> %s).", interval_start, interval_end)
            print(f"Posted interval: [{interval_start.isoformat()} -> {interval_end.isoformat()})")

        time.sleep(2)  # optional delay to avoid hammering the endpoint


def main():
    logging.info("=== Starting Hourly NLU Fallback Sync ===")
    # Load DB creds from endpoints.yml (and env)
    db_creds = load_db_credentials("/usr/src/app/endpoints.yml")
    fill_missing_hourly_intervals(db_creds)
    logging.info("=== Finished Hourly NLU Fallback Sync ===")


if __name__ == "__main__":
    main()
