import asyncio
import nest_asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os
import requests
from dotenv import load_dotenv
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

nest_asyncio.apply()  # Needed to run interactive python

load_dotenv()

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
        self.session : Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that can use tools to answer questions."
            }
        ]

    async def connect_mcp_server(self,server_params):
        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # async with stdio_client(server_params) as (read_stream, write_stream):
        #     async with ClientSession(read_stream, write_stream) as session:
        # Initialize the connection
        await self.session.initialize()

        # List available tools
        tools_result = await self.session.list_tools()
        print("Available tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

        # Call our calculator tool
        result = await self.session.call_tool("add", arguments={"a": 2, "b": 3})
        print(f"2 + 3 = {result.content[0].text}")


    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
            """Get available tools from the MCP server in OpenAI format.

            Returns:
                A list of tools in OpenAI format.
            """
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
            """Process a query using OpenAI and available MCP tools.

            Args:
                query: The user query.

            Returns:
                The response from OpenAI.
            """
            # Get available tools
            tools = await self.get_mcp_tools()

            # Add user message
            self.messages.append({
                "role": "user",
                "content": query
            })
            # Prepare payload
            payload = {
                "messages": self.messages,
                "model": "openai/gpt-4o-mini",
                "temperature": 1,
                "top_p": 1,
                "tools": tools,
                "tool_choice": "auto"
            }
        
            # Add tools if available
            # if tools:
            #     payload["tools"] = tools
            #     payload["tool_choice"] = "auto"

            # Send request
            response = requests.post(API_URL, headers=HEADERS, params=PARAMS, json=payload, verify=False)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]

            # # Handle tool calls if present
            # if "tool_calls" in message:
            #     print("🔧 Tool calls:", message["tool_calls"])
            #     self.messages.append(message)

            #     for tool_call in message["tool_calls"]:
            #         tool_name = tool_call['function']['name']
            #         arguments = tool_call['function']['arguments']
                    
            #         # Parse arguments if they're a string
            #         if isinstance(arguments, str):
            #             arguments = json.loads(arguments)
                    
            #         # Execute the actual MCP tool
            #         tool_result = await self.session.call_tool(
            #         tool_call['function']['name'],
            #         arguments=json.loads(tool_call['function']['arguments']),
            #     )
            #         print(f"✅ Executed '{tool_name}': {tool_result}")
                    
            #         self.messages.append({
            #             "role": "tool",
            #             "tool_call_id": tool_call["id"],
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": tool_result
            #                 }
            #             ]
            #         })
            # else:
                # No tool calls, return the response
            content = message.get("content", "")
            self.messages.append(message)
            return content


async def main():
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",  # The command to run your server
        args=["server.py"],  # Arguments to the command
    )
    client = MCPClient()
    await client.connect_mcp_server(server_params)

    while True:
        user_input = input(">> ")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Exiting the chat...")
            break

        try:
            response = await client.process_query(user_input)
            print(f"🤖 Assistant: {response}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            

if __name__ == "__main__":
    asyncio.run(main())