"""Bonus for chapter 5 - the same retriever tools, served over MCP.

Any MCP host (Claude Desktop, Claude Code, IDE agents, ...) can then act as the
"retriever router": it reads the tool descriptions and decides what to call.

    pip install "mcp>=2,<3"
    python ch05_mcp_server.py            # stdio transport

Example host config (stdio):
    {"mcpServers": {"movies-graph": {"command": "python",
                                     "args": ["/path/to/code/ch05_mcp_server.py"]}}}
"""
from __future__ import annotations

import ch05_agentic_rag as agent
from mcp.server.mcpserver import MCPServer  # MCP Python SDK v2 (FastMCP was renamed)

server = MCPServer("movies-graph")


@server.tool()
def movie_info_by_title(title: str) -> list[dict]:
    """Get information about a movie (release year, tagline, cast, directors) by title."""
    return agent.movie_info_by_title(title)


@server.tool()
def movies_info_by_actor(actor: str) -> list[dict]:
    """Get the movies an actor has acted in, with cast and directors."""
    return agent.movies_info_by_actor(actor)


@server.tool()
def ask_movie_database(question: str) -> list[dict]:
    """Answer counting / ranking / filtering questions by generating a read-only AQL query.
    Use only when the other tools don't fit."""
    return agent.text2aql_tool(question)


if __name__ == "__main__":
    agent.init()
    server.run(transport="stdio")
