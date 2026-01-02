import os
import json
import time
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SESSION_DIR = "sessions"
MAX_IDLE_TIME = 1800  # 30 minutes in seconds

SESSION_DIR = "/tmp"

# --- CONTEXT HELPERS ---
def get_history_file(user_id):
    # Sanitize user_id for filename
    safe_id = "".join([c for c in user_id if c.isalnum()])[:50]
    return os.path.join(SESSION_DIR, f"{safe_id}.json")

def load_user_context(user_id):
    path = get_history_file(user_id)
    if os.path.exists(path):
        # Reset if the file is older than 30 minutes
        if time.time() - os.path.getmtime(path) > MAX_IDLE_TIME:
            os.remove(path)
            return []
        with open(path, 'r') as f:
            return json.load(f)
    return []

def save_user_context(user_id, history):
    path = get_history_file(user_id)
    with open(path, 'w') as f:
        json.dump(history, f)

# --- ALEXA HANDLER ---
@app.route('/chat', methods=['POST']) # Alexa points here
def chat():
    data = request.json
    
    # 1. Identify the Request Type and User
    req_type = data.get("request", {}).get("type")
    user_id = data.get("session", {}).get("user", {}).get("userId", "default_user")

    # 2. Handle Skill Launch
    if req_type == "LaunchRequest":
        return alexa_response("Welcome to Gemini. How can I help you today?")

    # 3. Handle User Input (IntentRequest)
    if req_type == "IntentRequest":
        # Get the query from Alexa's 'query' slot
        slots = data['request']['intent'].get('slots', {})
        user_message = slots.get('query', {}).get('value', "")

        if not user_message:
            return alexa_response("I didn't quite catch that. Could you repeat it?")

        try:
            # Load existing context
            history = load_user_context(user_id)
            
            # Start Chat with history
            chat_session = client.chats.create(
                model="gemini-2.5-flash",
                history=history,
                config=types.GenerateContentConfig(
                    temperature=0.5,       
                    max_output_tokens=500  
                )
            )
            
            response = chat_session.send_message(user_message)
            
            # Save updated history (Convert parts to text strings for JSON)
            updated_history = []
            for msg in chat_session.history:
                updated_history.append({
                    "role": msg.role,
                    "parts": [{"text": p.text} for p in msg.parts]
                })
            save_user_context(user_id, updated_history)

            return alexa_response(response.text)
            
        except Exception as e:
            return alexa_response(f"Sorry, I ran into an error: {str(e)}")

    return alexa_response("I'm not sure how to handle that request.")

def alexa_response(text):
    """Formats the JSON response for the Alexa Skills Kit"""
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": False  # Keeps the session open for a follow-up
        }
    })

if __name__ == "__main__":
    app.run(debug=True)






