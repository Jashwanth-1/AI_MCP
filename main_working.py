import os
import json
import asyncio
import nest_asyncio
import chainlit as cl
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
import requests

nest_asyncio.apply()
load_dotenv()

#Tool Calling not present in the gpt-4o-mini model. I will need gpt-4 model. It also does not support native streaming

os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

API_URL = "https://models.github.ai/inference/v1/chat/completions"
API_KEY = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
PARAMS = {
    "api-version": "2024-08-01-preview"
}


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that can use tools to answer questions."
            }
        ]

    async def connect_mcp_server(self, server_params):
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]

    async def process_query(self, query: str) -> str:
        tools = await self.get_mcp_tools()
        self.messages.append({
            "role": "user",
            "content": query
        })

        payload = {
            "messages": self.messages,
            "model": "openai/gpt-4o-mini",
            "temperature": 1,
            "top_p": 1,
            # "tools": tools,
            # "tool_choice": "auto"
        }

        

        response = requests.post(API_URL, headers=HEADERS, params=PARAMS, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content", "")
        self.messages.append(message)
        return content


# Chainlit entry point
client = MCPClient()

@cl.on_chat_start
async def on_chat_start():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )
    await client.connect_mcp_server(server_params)
    await cl.Message(content="✅ MCP client connected. Ask me anything!").send()

@cl.on_message
async def on_message(message: cl.Message):
    try:
        msg = cl.Message(content="")
        await msg.send()

        # Get response from your LLM
        response = await client.process_query(message.content)

        # Stream the response character by character (or chunk by chunk)
        for chunk in response:
            await msg.stream_token(chunk)
            await asyncio.sleep(0.02)

        # Finalize the message
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"❌ Error: {str(e)}").send()
