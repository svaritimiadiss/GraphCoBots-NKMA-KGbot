#!/usr/bin/env python3
"""
Weekly User Retention Rate (UTC) - Multi-week sync (Monday to Monday)

Definition of a returning user:
 - A user who appears on MORE THAN ONE DISTINCT UTC DAY within the same Monday->Monday interval.

Key Features:
  - If server has no data, we default to earliest event in our DB.
  - We generate Monday->Monday intervals from that server date up to the current Monday boundary.
  - For each interval, we compute:
    - total_users
    - returning_users (usage_day_count>1)
    - returning_users_last_active: a list of unique days (YYYY-MM-DD) for each returning user
    - retention rate = (returning_users / total_users) * 100
    - first_time_users = distinct users who appear before the interval's end_datetime
  - Post each missing interval to ANALYTICS_POST_URL,
    accepting either 200 or 201 as success.

Environment variables used:
  - ANALYTICS_GET_URL (for checking server's latest end_datetime)
  - ANALYTICS_POST_URL (for posting new intervals)
  - DB credentials loaded from /usr/src/app/endpoints.yml
"""

import os
import json
import yaml
import psycopg2
import logging
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from collections import defaultdict
import time
from pathlib import Path


# Get the root directory (assuming your script is in a subfolder)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # Adjust based on depth

# Load the .env file from the root directory
dotenv_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path)

# Setup logging
APP_PATH = os.getenv("APP_PATH", "/app")
LOG_DIR = f"{APP_PATH}/logs"
# LOG_DIR = "/usr/src/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# Environment variables for GET / POST
ANALYTICS_GET_URL = os.getenv('RETENTION_RATE_ANALYTICS_GET_URL')
ANALYTICS_POST_URL = os.getenv('RETENTION_RATE_ANALYTICS_POST_URL')


def load_db_credentials(endpoints_yml_path):
    """
    Load DB credentials from endpoints.yml.
    """
    # try:
    #     with open(endpoints_yml_path, 'r') as f:
    #         endpoints_data = yaml.safe_load(f)
    # except Exception as e:
    #     logging.error("Error reading endpoints.yml: %s", e)
    #     raise

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


def parse_iso_to_utc_dt(iso_str):
    """
    Convert e.g. '2025-02-24T00:00:00Z' -> datetime(2025,2,24,0,0,0, tz=ZoneInfo('UTC')).
    Return None if invalid or iso_str is None.
    """
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        logging.error("Failed to parse iso string: %s", iso_str)
        return None


def compute_monday_start(dt_utc):
    """
    Given dt_utc, find the most recent Monday 00:00:00 (UTC) on or before dt_utc.
    This ensures alignment to Monday boundaries.
    """
    # Monday=0, Tuesday=1,... Sunday=6
    offset_days = dt_utc.weekday()
    monday_utc = dt_utc - timedelta(days=offset_days)
    return monday_utc.replace(hour=0, minute=0, second=0, microsecond=0)


def generate_week_intervals(start_monday, end_monday):
    """
    Generate a list of [monday -> next_monday) intervals
    from start_monday up to (not including) end_monday.
    """
    intervals = []
    current_start = start_monday
    while current_start < end_monday:
        next_monday = current_start + timedelta(days=7)
        if next_monday > end_monday:
            next_monday = end_monday
        intervals.append((current_start, next_monday))
        current_start = next_monday
    return intervals


def get_server_latest_end_dt(assistant_botid):
    """
    GET the server's last recorded end_datetime for assistant_botid.
    Returns a parsed datetime in UTC or None if not found/error.
    Example response: {"end_datetime": "2025-02-24T00:00:00Z"}
                     or {"message": "No records found ..."}
    """
    if not ANALYTICS_GET_URL:
        logging.warning("ANALYTICS_GET_URL not set, skipping GET sync.")
        return None

    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }

    try:
        resp = requests.get(ANALYTICS_GET_URL, headers=headers, timeout=15)
        logging.info("GET status: %d", resp.status_code)
        logging.info("GET body: %s", resp.text)
        if resp.status_code == 200:
            data = resp.json()
            iso_str = data.get("end_datetime")
            return parse_iso_to_utc_dt(iso_str)  # Could be None
        else:
            logging.warning("GET returned status %d", resp.status_code)
            return None
    except Exception as e:
        logging.error("Error in GET request: %s", e)
        return None


def earliest_db_timestamp_utc(db_host, db_name, db_user, db_password, db_port):
    """
    Query earliest event timestamp from the DB. Return as a UTC datetime.
    If no events or error, return None.
    """
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
        cursor.execute("SELECT MIN(timestamp) FROM events;")
        row = cursor.fetchone()
        if not row or not row[0]:
            logging.warning("No events found in DB (MIN timestamp is null).")
            return None
        min_ts = float(row[0])
        earliest_dt = datetime.fromtimestamp(min_ts, tz=ZoneInfo("UTC"))
        return earliest_dt
    except Exception as e:
        logging.error("Error retrieving earliest DB timestamp: %s", e)
        return None
    finally:
        if conn:
            conn.close()


def post_data(payload, assistant_botid):
    """
    POST the final weekly retention payload to ANALYTICS_POST_URL.
    Return True if status is 200 or 201, else False.
    """
    if not ANALYTICS_POST_URL:
        logging.warning("ANALYTICS_POST_URL not set, skipping POST.")
        return False

    headers = {
        'Content-Type': 'application/json',
        'assistant-botid': 'exhibition-bot-kazantzakis'
    }
    logging.info("Posting to %s, payload=%s", ANALYTICS_POST_URL, payload)
    try:
        payload_str = json.dumps(payload, default=float)
        resp = requests.post(ANALYTICS_POST_URL, data=payload_str, headers=headers)
        logging.info("POST status: %d", resp.status_code)
        logging.info("POST response: %s", resp.text)
        # Accept both 200 and 201 as success
        return (resp.status_code in [200, 201])
    except Exception as e:
        logging.error("Error in POST request: %s", e)
        return False


def weekly_retention_rate(db_host, db_name, db_user, db_password, db_port, start_dt, end_dt):
    """
    Return:
      - retention_rate_pct
      - returning_users_count
      - total_users_count
      - usage_days_dict (for returning users, unique days only)
      - conn
    for [start_dt, end_dt), with "returning user" = usage_day_count>1.

    We store only the distinct YYYY-MM-DD for each returning user's usage
    within the interval, not detailed timestamps.
    """
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

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
        logging.info("Connected to DB successfully.")
    except Exception as e:
        logging.error("Error connecting to DB: %s", e)
        return 0.0, 0, 0, {}, None

    # 1) total_users & returning_users_count
    #    'returning' means usage_day_count>1
    weekly_retention_query = f"""
    WITH weekly_data AS (
      SELECT 
        sender_id,
        COUNT(DISTINCT to_timestamp(timestamp)::date) AS usage_day_count
      FROM events
      WHERE to_timestamp(timestamp) >= '{start_str}'
        AND to_timestamp(timestamp) <  '{end_str}'
      GROUP BY sender_id
    ),
    weekly_users AS (
      SELECT sender_id
      FROM weekly_data
    ),
    returning_users AS (
      SELECT sender_id
      FROM weekly_data
      WHERE usage_day_count > 1
    )
    SELECT
      (SELECT COUNT(*) FROM returning_users) AS returning_users_count,
      (SELECT COUNT(*) FROM weekly_users)    AS total_users_count,
      (
        (SELECT COUNT(*) FROM returning_users) * 100.0
        / NULLIF((SELECT COUNT(*) FROM weekly_users), 0)
      ) AS retention_rate
    """
    returning_users_count = 0
    total_users_count = 0
    retention_rate_pct = 0.0
    try:
        cursor.execute(weekly_retention_query)
        row = cursor.fetchone()
        if row:
            returning_users_count, total_users_count, retention_rate_pct = row
        logging.info(
            "[%s->%s) returning=%d, total=%d, retention=%.2f%%",
            start_str, end_str, returning_users_count, total_users_count, retention_rate_pct
        )
    except Exception as e:
        logging.error("Error executing weekly retention query: %s", e)

    # 2) Gather only the *unique days* for returning users
    usage_query = f"""
    WITH weekly_data AS (
      SELECT 
        sender_id,
        COUNT(DISTINCT to_timestamp(timestamp)::date) AS usage_day_count
      FROM events
      WHERE to_timestamp(timestamp) >= '{start_str}'
        AND to_timestamp(timestamp) <  '{end_str}'
      GROUP BY sender_id
    ),
    returning_users AS (
      SELECT sender_id
      FROM weekly_data
      WHERE usage_day_count > 1
    )
    SELECT e.sender_id, to_timestamp(e.timestamp)::date AS usage_date
    FROM events e
    JOIN returning_users ru ON e.sender_id = ru.sender_id
    WHERE to_timestamp(e.timestamp) >= '{start_str}'
      AND to_timestamp(e.timestamp) <  '{end_str}'
    ORDER BY e.sender_id, usage_date;
    """
    returning_users_days = defaultdict(set)
    try:
        cursor.execute(usage_query)
        for sid, usage_date in cursor.fetchall():
            date_str = usage_date.strftime("%Y-%m-%d")  # no time
            returning_users_days[sid].add(date_str)
    except Exception as e:
        logging.error("Error fetching returning usage days: %s", e)

    # convert each set -> a sorted list
    usage_days_dict = {}
    for sid, day_set in returning_users_days.items():
        sorted_days = sorted(list(day_set))
        usage_days_dict[sid] = sorted_days

    return retention_rate_pct, returning_users_count, total_users_count, usage_days_dict, conn


def compute_first_time_users_by_end(conn, end_dt):
    """
    Count distinct sender_id in the DB up to the interval's end_datetime.
    That is, all events where to_timestamp(timestamp) < end_dt.
    """
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor = conn.cursor()
        query = f"""
        SELECT COUNT(DISTINCT sender_id)
        FROM events
        WHERE to_timestamp(timestamp) < '{end_str}';
        """
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        logging.error("Error computing first_time_users by end_dt: %s", e)
        return 0
    finally:
        cursor.close()


def main():
    logging.info("Starting multi-week sync retention script with returning-user as usage_day_count>1.")
    # 1) Load DB credentials
    try:
        db_host, db_name, db_user, db_password, db_port = load_db_credentials("/usr/src/app/endpoints.yml")
    except Exception as e:
        logging.error("Failed to load DB credentials: %s", e)
        return
    logging.info("Using assistant-botid=exhibition-bot-kazantzakis")

    # 2) GET the server's last known end_datetime
    server_end_dt = get_server_latest_end_dt(db_name)
    if server_end_dt is None:
        # If the server returns no data or "No records found",
        # default to earliest event in DB
        earliest_dt = earliest_db_timestamp_utc(db_host, db_name, db_user, db_password, db_port)
        if earliest_dt:
            server_end_dt = earliest_dt
            logging.info("Defaulting server_end_dt to earliest DB timestamp: %s", server_end_dt)
        else:
            # If no events at all in DB, there's nothing to post
            logging.warning("No events in DB, so no data to post. Exiting.")
            return

    # 3) Determine the current Monday boundary
    now_utc = datetime.now(tz=ZoneInfo("UTC"))
    local_monday = compute_monday_start(now_utc)

    if server_end_dt >= local_monday:
        logging.info("Server end_datetime=%s >= local Monday=%s; up-to-date.", server_end_dt, local_monday)
        return

    # 4) Generate intervals from server's Monday boundary up to local Monday
    server_monday = compute_monday_start(server_end_dt)
    intervals = generate_week_intervals(server_monday, local_monday)
    logging.info("We have %d missing weekly intervals to post.", len(intervals))

    # 5) For each interval, compute retention & post
    for (start_dt, end_dt) in intervals:
        ret_rate_pct, returning_users, total_users, usage_days_dict, conn = weekly_retention_rate(
            db_host, db_name, db_user, db_password, db_port,
            start_dt, end_dt
        )
        if not conn:
            logging.error("No DB connection, skipping the rest.")
            break

        # Instead of counting all time, count only up to end_dt
        first_time = compute_first_time_users_by_end(conn, end_dt)
        conn.close()

        ret_decimal = round(ret_rate_pct / 100, 3)
        start_iso = start_dt.isoformat(timespec='seconds').replace("+00:00", "Z")
        end_iso = end_dt.isoformat(timespec='seconds').replace("+00:00", "Z")

        # Build final JSON
        payload = {
            "graph_type_id": "gid0002",
            "retention_rate": ret_decimal,
            "returning_users": returning_users,
            "total_users": total_users,
            "returning_users_last_active": usage_days_dict,
            "start_datetime": start_iso,
            "end_datetime": end_iso,
            "first_time_users": first_time
        }

        success = post_data(payload, db_name)
        if not success:
            logging.error("POST failed for [%s->%s), stopping sync.", start_iso, end_iso)
            break
        else:
            logging.info("Successfully posted interval [%s->%s).", start_iso, end_iso)

        # Optional small delay
        time.sleep(2)


if __name__ == "__main__":
    main()
