# gid0001: Hourly Active Unique Users

## Overview

This script aggregates unique user interactions from it's Rasa Chatbot's PostgreSQL tracker store. The Python script runs every 1 hour (triggered via a cron job) and posts a JSON payload with the aggregated Hourly Active Users (HAU) data to a Bot Analytics API /store_daily_active_users endpoint.

## Features

- **Timezone-Aware Timestamps:**  
  Splits data into discrete 1‐hour blocks (e.g., 09:00–10:00, 10:00–11:00) in UTC timezone.
- **Aggregates Unique Users:**  
  Counts all unique users (based on `sender_id`) over the past 1 hour by quering into the Rasa Tracker Store Azure Postgres db.
- **Scheduled Execution:**  
  Triggered every 1 hour via a cron job from server.sh file.
- **Auto‐Detection of Missing Hours:**  
  If the script or service was down, it will catch up by filling all skipped intervals.
- **POST behavior:**
  Ignores hours already posted (returns `409 Conflict due to Duplicate data`).


## Input format
```bash
headers = {
  "Content-Type": "application/json",
  "assistant-botid": db_name  # from endpoints.yml the db name
  }
```

## Payload
```bash
{
  "graph_type_id": "gid0001",
  "start_datetime": start_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
  "end_datetime": end_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
  "users_count": user_count
}
```
