import os
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Initialize Gemini Client
# Vercel will pull the API key from Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def index():
    return "Gemini Flask API is running!"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=user_message
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Required for local testing
if __name__ == "__main__":
    app.run(debug=True)