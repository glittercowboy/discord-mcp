# Technology Stack

**Analysis Date:** 2026-01-23

## Languages

**Primary:**
- Python 3.12+ - Core MCP server implementation in `src/server.py`

## Runtime

**Environment:**
- Python 3.12 (specified in `.python-version`)

**Package Manager:**
- uv - Package manager for dependency resolution
- Lockfile: `uv.lock` (present)

## Frameworks

**Core:**
- mcp[cli] 1.25.0+ - Model Context Protocol server framework via `FastMCP` from `mcp.server.fastmcp`
- httpx 0.28.1+ - HTTP client library for Discord API communication

## Key Dependencies

**Critical:**
- mcp[cli] >= 1.25.0 - Base MCP server framework for exposing Discord operations as tools
- httpx >= 0.28.1 - Async HTTP client for making REST requests to Discord API endpoints

**Transitive (from mcp):**
- pydantic - Data validation and settings management
- pydantic-settings - Configuration management from environment variables
- click - CLI framework for MCP server invocation
- jsonschema - JSON schema validation for operation parameters
- cryptography - TLS/SSL support for httpx
- pyjwt - JWT handling for authentication
- h11 - HTTP/1.1 protocol implementation
- httpcore - Low-level HTTP transport for httpx

## Configuration

**Environment:**
- `DISCORD_BOT_TOKEN` - Discord bot authentication token (required)
- `DISCORD_GUILD_ID` - Target Discord server ID (required)
- Configured via Claude Desktop `claude_desktop_config.json` or Claude Code MCP settings

**Build:**
- pyproject.toml - Project metadata and dependencies
- Specifies Python >= 3.12 requirement

## Platform Requirements

**Development:**
- Python 3.12 or higher
- uv package manager
- Working Discord developer account
- Admin permissions on target Discord server

**Production:**
- Python 3.12 or higher runtime
- Access to Discord API (https://discord.com/api/v10)
- Valid Discord bot token
- Target guild ID configured

## Deployment

**Execution Model:**
- Runs as subprocess via uv command from MCP server configuration
- Command: `uv --directory /path/to/discord-mcp run python -m src.server`
- Invoked by Claude Desktop or Claude Code when tools are called
- Uses REST API only (no WebSocket Gateway connection)
- Stateless per-request operation model

---

*Stack analysis: 2026-01-23*
