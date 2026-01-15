import requests
# import os
# import yaml
# from dotenv import load_dotenv, set_key
from rasa_sdk.executor import CollectingDispatcher

# # Load the responses from the JSON file just ONCE
# with open('actions/genai_placeholders.yml', 'r', encoding='utf-8') as f:
#     genai_data = yaml.safe_load(f)

# load_dotenv()

# GENAI_BASE_URL = os.getenv("FASTAPI_APP_URL")
# FALLBACK_ENDPOINT = os.getenv("FALLBACK_ENDPOINT")

def action_openai_chat_completion(
    dispatcher: CollectingDispatcher,
    system_prompt: str,
    user_prompt: str,
    chat_model: str,
    endpoint_url: str
) -> None:

    params = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "chat_model": chat_model,
    }

    try:
        text_response = requests.get(endpoint_url, params=params).json()
        dispatcher.utter_message(text=text_response)
    except requests.exceptions.RequestException as e:
        dispatcher.utter_message(
            text="Συγγνώμη, υπήρξε κάποιο πρόβλημα κατά την επεξεργασία του ερωτήματός σου."
        )
        print(f"API request failed: {e}")