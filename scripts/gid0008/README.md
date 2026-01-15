# gid0008: Hourly NLU Fallbacks

## Overview
This script calculates hourly nlu_fallback intents of a Rasa chatbot. It identifies each instance where the chatbot could not correctly classify the user’s intent and captures relevant details such as the sender_id and text of the fallback messages.

## Features
- **1-Hour Windows:**
  The script snaps both the server’s last known posting time and the local system’s current time to the top of the hour (UTC). It then iterates hour by hour until it reaches the present.
- **Fallback Messages:**
  Any user event (type_name = 'user') whose intent.name == "nlu_fallback" is considered a fallback. For each fallback, the script saves the sender_id and the text message.
- **Missing Data Sync:**
  On start, the script GETs your server’s last known end_datetime.
  If the server has no records, the script defaults to the earliest user-event timestamp in your database.
  It then iterates over each missing hour interval from the last known endpoint up to the current hour boundary, calculates fallback data, and POSTs it to the remote server.
- **Total Fallback Count:**
  For each interval, the script reports how many fallback events occurred (total_fallback_count).


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
  "graph_type_id": "gid0008",
  "start_datetime": "2025-02-19T09:00:00Z",
  "end_datetime": "2025-02-19T10:00:00Z",
  "total_fallback_count": 2,
  "fallback_messages": [
    {
      "sender_id": "front-webchat-Neh-1737364930",
      "text": "EXTERNAL: advanced rocket science??"
    },
    {
      "sender_id": "front-webchat-Usr-984563210",
      "text": "Που είναι το μουσείο;"
    }
  ]
}
```
