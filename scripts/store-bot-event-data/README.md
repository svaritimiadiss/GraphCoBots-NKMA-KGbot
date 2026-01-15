# Store Bot Event Data

## Overview

The primary goal of this script is to:

1. Connect to a Rasa bot’s Postgres tracker store.
2. Retrieve all raw event records beyond the last processed event ID.
3. Post the new events in json format (plus a header key-value `assistant_botid`) to the designated Bot Analytics Service for further analytics, storage, or additional processing.



---

## Features

This repository contains a Python service that every 1 hour using a CRON job:

1. **Reads configuration** from:
   - `endpoints.yml` for Azure PostgreSQL connection details (host, db, user, password).
   - Environment variables (in `.env` or set in your shell) e.g. `POST_URL` and `LAST_ID_ENDPOINT`.
2. **Logs** into `app.log` for troubleshooting.
3. **Makes a GET request** to `LAST_ID_ENDPOINT` with the header `assistant-botid: <db_name>` to find out the last processed event ID.
4. **Queries** for all new rows where `id > last_processed_id`.
5. **Posts** these new rows (in JSON format keyed by their record ID) to the `POST_URL`, using the same custom `assistant-botid` header e.g. "Aegeas-el".
6. **Handles missing data** by retrying any missed IDs if the POST endpoint returns an error payload.

---

## Environment Variables

- **`POST_URL`**: The endpoint to which the new data should be posted.  
- **`LAST_ID_ENDPOINT`**: The endpoint from which we fetch the “last processed event ID.”  

## Payload example

```
{
  "14538": { ... },
  "14539": { ... },
  "14540": { ... }
}
```

