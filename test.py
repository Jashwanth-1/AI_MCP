import os
import requests
from dotenv import load_dotenv

# Disable TLS verification (not recommended for production)
os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

load_dotenv()

# API configuration
API_URL = "https://models.github.ai/inference/v1/chat/completions"
API_KEY = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
PARAMS = {
    "api-version": "2024-08-01-preview"
}

# Initial system message
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    }
]

def run_chat():
    print("Chat started. Type 'exit' to end the conversation.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting the chat...")
            break

        # Append user message
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_input
                }
            ]
        })

        # Prepare payload
        payload = {
            "messages": messages,
            "model": "openai/gpt-4o-mini",
            "temperature": 1,
            "top_p": 1
        }

        # Send request
        response = requests.post(API_URL, headers=HEADERS, params=PARAMS, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()

        # Extract and display response
        choice = data["choices"][0]
        message = choice["message"]

        if "tool_calls" in message:
            print("Tool calls:", message["tool_calls"])
            messages.append(message)

            for tool_call in message["tool_calls"]:
                tool_result = f"Executed tool: {tool_call['function']['name']}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": [
                        {
                            "type": "text",
                            "text": tool_result
                        }
                    ]
                })
        else:
            content = message.get("content", "")
            if isinstance(content, list):
                text_reply = next((c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"), "")
            else:
                text_reply = content
            print(f"Bot: {text_reply}")
            messages.append(message)


run_chat()
