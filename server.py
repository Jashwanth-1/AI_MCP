"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from openai import OpenAI
from dotenv import load_dotenv
import os,asyncio,json

load_dotenv()

# Create an MCP server
mcp = FastMCP(
    name = "FirstMCPServer",
    host = "127.0.0.1",
    port=8080
)

client = OpenAI(
        base_url = "https://models.github.ai/inference",
        api_key = os.getenv("GITHUB_TOKEN"),
        default_headers = {
            "api-version": "2024-08-01-preview",
        },
    )

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool(
    name="Query Database (BOMSSTEST517)",
    description="Query zoom rooms, zoom devices from Database based on the provided query"
)
def query_db(sql_query: str) -> list[dict]:
    """Query the database using provided SQL query"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        result = session.execute(text(sql_query))
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        session.close()

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }
    return f"{styles.get(style, styles['friendly'])} for someone named {name}."

if __name__ == "__main__":
    mcp.run(transport="stdio")
    # mcp.run(
    #     transport="streamable-http"
    # )