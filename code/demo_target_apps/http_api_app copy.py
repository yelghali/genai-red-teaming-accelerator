"""
HTTP API Demo Target Application
FastAPI-based chatbot that uses Azure OpenAI
"""

import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import shutil
from openai import AzureOpenAI

app = FastAPI()
CONV_FILE = "conversations.json"

# Azure OpenAI client
azure_openai_client = AzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('OPENAI_CHAT_API_KEY'),
    api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview'),
)

class PromptRequest(BaseModel):
    user_prompt: str
    conversation_id: str

def load_conversations():
    if not os.path.exists(CONV_FILE):
        return {}
    try:
        with open(CONV_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load conversations ({e}), starting fresh.")
        return {}

def save_conversations(conversations):
    temp_fd, temp_path = tempfile.mkstemp()
    try:
        with os.fdopen(temp_fd, "w") as tmpf:
            json.dump(conversations, tmpf)
        shutil.move(temp_path, CONV_FILE)
    except Exception as e:
        print(f"Error saving conversations: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat")
async def chat(req: PromptRequest):
    print(f"Received: user_prompt={repr(req.user_prompt)} conversation_id={repr(req.conversation_id)}")
    
    if not req.user_prompt or not req.conversation_id:
        raise HTTPException(status_code=400, detail="user_prompt and conversation_id are required")
    
    conversations = load_conversations()
    conv = conversations.get(req.conversation_id, [])
    conv.append({"role": "user", "content": req.user_prompt})
    
    try:
        response = azure_openai_client.chat.completions.create(
            model=os.getenv('OPENAI_CHAT_MODEL'),
            messages=conv,
            max_tokens=1000,
            temperature=0.7,
            stream=False
        )
        
        data = response.choices[0].message
        conv.append({"role": "assistant", "content": data.content})
        conversations[req.conversation_id] = conv
        save_conversations(conversations)
        
        print("Returning response:", json.loads(response.to_json()))
        return json.loads(response.to_json())
        
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        raise HTTPException(status_code=500, detail="Error processing request")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
