"""
Playwright Web Demo Target Application
Flask-based web chatbot interface
"""

from flask import Flask, render_template_string, request, jsonify
import os
from pathlib import Path
from openai import AzureOpenAI
import dotenv

# Load environment variables from code/.env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

# Set AZURE_OPENAI_API_KEY for SDK compatibility
if os.getenv('OPENAI_CHAT_API_KEY'):
    os.environ['AZURE_OPENAI_API_KEY'] = os.getenv('OPENAI_CHAT_API_KEY')

app = Flask(__name__)

# Azure OpenAI client
azure_openai_client = AzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('OPENAI_CHAT_API_KEY'),
    api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview'),
)

# Store conversation history in memory
conversations = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Demo Chatbot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        #chat-container {
            border: 1px solid #ddd;
            height: 400px;
            overflow-y: scroll;
            padding: 20px;
            margin-bottom: 20px;
            background-color: #f9f9f9;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #e3f2fd;
            text-align: right;
        }
        .bot-message {
            background-color: #f1f8e9;
        }
        #input-container {
            display: flex;
            gap: 10px;
        }
        #message-input {
            flex: 1;
            padding: 10px;
            font-size: 16px;
        }
        #send-button {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #4caf50;
            color: white;
            border: none;
            cursor: pointer;
        }
        #send-button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <h1>Demo Chatbot</h1>
    <div id="chat-container"></div>
    <div id="input-container">
        <input type="text" id="message-input" placeholder="Type your message...">
        <button id="send-button">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user-message' : 'bot-message');
            messageDiv.textContent = content;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            messageInput.value = '';
            sendButton.disabled = true;

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                addMessage(data.response, false);
            } catch (error) {
                addMessage('Error: Could not get response', false);
            }

            sendButton.disabled = false;
            messageInput.focus();
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    session_id = request.remote_addr  # Use IP as session ID
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Get or create conversation
    if session_id not in conversations:
        conversations[session_id] = []
    
    conversations[session_id].append({"role": "user", "content": message})
    
    try:
        response = azure_openai_client.chat.completions.create(
            model=os.getenv('OPENAI_CHAT_MODEL'),
            messages=conversations[session_id],
            max_tokens=1000,
            temperature=0.7,
            stream=False
        )
        
        bot_response = response.choices[0].message.content
        conversations[session_id].append({"role": "assistant", "content": bot_response})
        
        return jsonify({"response": bot_response})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to get response"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
