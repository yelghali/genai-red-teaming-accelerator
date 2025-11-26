import logging
import os

from flask import Flask, jsonify, render_template, request
from openai import AzureOpenAI

# This web app is for testing the Playwright Target. Do not use it in production.

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__, template_folder="./")

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("OPENAI_CHAT_API_KEY")
DEPLOYMENT_NAME = os.getenv("OPENAI_CHAT_MODEL")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, DEPLOYMENT_NAME]):
    raise ValueError("Missing required environment variables: AZURE_OPENAI_ENDPOINT, OPENAI_CHAT_API_KEY, OPENAI_CHAT_MODEL")

# Initialize Azure OpenAI client
openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    api_version=API_VERSION,
)

# Define the system prompt
SYSTEM_PROMPT = {"role": "system", "content": "You are a helpful bot answering questions."}


def get_answer(messages) -> str:
    """
    Sends the conversation messages to the Azure OpenAI GPT-4 model and retrieves the bot's response.

    Args:
        messages (list): A list of message dictionaries.

    Returns:
        str: The content of the bot's response.
    """
    try:
        # Prepend the system prompt to the messages
        full_messages = [SYSTEM_PROMPT] + messages
        logging.debug(f"Full messages sent to model: {full_messages}")

        # Send the messages to the Azure OpenAI GPT-4 model
        response = openai_client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=full_messages,
            max_tokens=500,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
        )

        # Extract and return the content of the bot's reply
        return response.choices[0].message.content

    except Exception as e:
        logging.error("Error in get_answer", exc_info=True)
        return "I'm sorry, something went wrong while processing your request."


@app.route("/")
def index():
    """
    Renders the main page of the chat application.
    """
    return render_template("index.html")


@app.route("/send_message", methods=["POST"])
def send_message():
    """
    Handles incoming messages from the user and returns the bot's response.

    Expects:
        JSON payload with a 'messages' key containing a list of user messages.

    Returns:
        JSON response with 'user_message' and 'bot_message'.
    """
    try:
        user_messages = request.json.get("messages", [])
        if not isinstance(user_messages, list):
            raise ValueError("'messages' should be a list of message objects.")

        # Get the bot's answer
        bot_response = get_answer(user_messages)

        return jsonify({"user_message": user_messages, "bot_message": bot_response})

    except Exception as e:
        logging.error("Exception in send_message", exc_info=True)
        return jsonify({"error": "An error occurred while processing your request."}), 500


if __name__ == "__main__":
    app.run(debug=True)