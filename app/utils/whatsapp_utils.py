import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.services.openai_service import generate_response

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")

def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )

def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        log_http_response(response)
        return response

def process_text_for_whatsapp(text):
    text = re.sub(r"\【.*?\】", "", text).strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    return text

def process_whatsapp_message(body):
    try:
        wa_id = body["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_body = message["text"]["body"]
        
        if message_body.lower() == "signup":
            response = "Click here to sign up: https://forms.google.com/signup_form"
        elif message_body.lower() == "knowledge":
            response = "Check out these resources: https://resources.example.com"
        elif message_body.lower() == "event":
            response = "Register for upcoming events: https://forms.google.com/event_registration"
        elif message_body.lower() == "community":
            response = "Join our discussion group: https://chat.whatsapp.com/invite/community_group"
        elif message_body.lower() == "idea":
            response = "Submit your idea here: https://forms.google.com/idea_submission"
        elif message_body.lower() == "help":
            response = (
                "Available Commands:\n"
                "- signup: Get the student signup link\n"
                "- knowledge: Access curated learning resources\n"
                "- event: Register for upcoming events\n"
                "- community: Join our discussion group\n"
                "- idea: Submit an idea for evaluation\n"
                "- help: Show this list of commands"
            )
        else:
            response = generate_response(message_body, wa_id, name)

        response = process_text_for_whatsapp(response)
        data = get_text_message_input(wa_id, response)
        send_message(data)

    except KeyError as e:
        logging.error(f"KeyError processing WhatsApp message: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing WhatsApp message: {e}")

def is_valid_whatsapp_message(body):
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
