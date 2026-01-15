# gid0007: Hourly Popular Intents

## Overview

This script calculates hourly user-intent frequencies for a Rasa chatbot. It iterates over each missing hour-long interval ([start_datetime, end_datetime)) from a certain “last posted” time up to the current hour (UTC), counting how many times each user intent appeared in that interval. It then posts these counts to an external analytics server, storing each hour’s data so you can visualize how often each intent is triggered over time.

## Features

- **1-Hour Windows:**
  The script snaps both the server’s last known posting time and the local system’s current time to the top of the hour (UTC). It then iterates hour by hour until it reaches the present.

- **Intent Counting:**
  For each hour, it queries the Rasa tracker store’s events table where type_name='user', grouping by intent_name. This reveals which intents users triggered and how often.

- **Sync Check with Server:**
  The script GETs the server’s latest end_datetime.
  If no entry is found, the script defaults to the earliest user event in your local database.
  It posts each missing 1-hour block via a POST request until it catches up to the current hour.

- **Duplicate Protection:**
  If the server already has data for a given (assistant-botid, start_datetime, end_datetime), it typically returns an error (e.g., HTTP 409). The script stops to avoid re-posting duplicates.

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
    "graph_type_id": "gid0007",
    "start_datetime": "2025-02-20T13:00:00Z",
    "end_datetime":   "2025-02-20T14:00:00Z",
    "triggered_intents_count": [
        {"intent_name": "welcome", "count": 10},
        {"intent_name": "faq",     "count": 5}
    ]
}
```
