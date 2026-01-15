# gid0002: Weekly User Retention Rate

## Overview

This scripts calculates weekly user retention for a Rasa chatbot. It computes how many users have interacted during a Monday-to-Sunday period (UTC timezone) and what fraction of those are “returning” users (i.e., those who had also interacted prior to that Monday). It also measures the first time users from the creation of the database.

## Features

- **Monday-to-Sunday Window:**

  The script calculates the start (start_datetime) at Monday 00:00 UTC and the end (end_datetime) at the next Monday 00:00 UTC, forming a half-open interval [start, end).
  
- **Returning Users:**

  A user is considered returning if they appear on more than one distinct day in the same weekly window. For example, if a user only shows up on Monday, they are not considered returning that week. If they also appear on Tuesday (or any subsequent day), they’re now returning.

- **First-Time Users:**

  For each interval, the script calculates first_time_users by counting all distinct users in the database whose timestamps are strictly before the interval’s end_datetime. This way, we get a historical total up to that week’s endpoint.

- **Retention Calculation:**

  - retention_rate: A decimal fraction = (returning_users / total_users), also stored as a float in the JSON.

  - returning_users: Among those, any user who also had an event before start_datetime.

  - total_users: Unique users who interacted in [start_datetime, end_datetime).

- **Multi-Week missing data Sync:**

  On start, the script GETs your server’s last known end_datetime.
  If the server has no records, the script defaults to the earliest event in your own database.
  The script then iterates over each missing Monday→Monday interval, calculates the retention data, and POSTs it to the remote server.



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
    "end_datetime": "2025-02-24T00:00:00Z",
    "graph_type_id": "gid0002",
    "retention_rate": 0.0,
    "returning_users": 0,
    "returning_users_last_active": {
"front-webchat-abc-1234": ["2025-02-10T10:15:00Z", "2025-02-11T08:07:00Z", ..., ...]
}
    "start_datetime": "2025-02-17T00:00:00Z",
    "total_users": 1,
    "first_time_users": first_time_users
}
```
