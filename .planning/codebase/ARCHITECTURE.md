# Architecture

**Analysis Date:** 2026-01-23

## Pattern Overview

**Overall:** MCP Tool Gateway with Operation Dispatch

This is a Model Context Protocol (MCP) server built with FastMCP that exposes Discord administrative operations through a centralized tool dispatcher. The architecture follows an on-demand discovery pattern where clients can explore available operations without pre-loading all tool definitions, then execute operations through a unified execution gateway.

**Key Characteristics:**
- Single-entry-point tool execution (discord_execute) that routes to category-specific handlers
- Declarative operation schema (operations.json) separate from handler logic
- Async/await throughout for non-blocking HTTP calls to Discord API
- Tight coupling to Discord.py API v10 with httpx for HTTP communication
- Format/transform layer that shapes raw Discord API responses for clarity

## Layers

**MCP Server Layer:**
- Purpose: Expose tools to Claude and other MCP clients
- Location: `src/server.py` (lines 1-23, entry point at bottom)
- Contains: FastMCP server initialization, three meta-tools, and the main event loop
- Depends on: FastMCP framework, handler functions, OPERATIONS schema
- Used by: MCP clients (Claude Desktop)

**Tool Definition Layer:**
- Purpose: Define what operations are available to clients
- Location: `src/operations.json` (1040 lines, 29 categories, 128 operations)
- Contains: Hierarchical operation schema with category descriptions, operation names, parameters, types, and requirement flags
- Depends on: Nothing (static JSON)
- Used by: discord_discover and discord_get_schema tools for client discovery

**Execution Layer:**
- Purpose: Route operations to appropriate handlers and manage errors
- Location: `src/server.py` (lines 203-228, discord_execute function)
- Contains: Operation string parsing, HANDLERS lookup, exception catching
- Depends on: HANDLERS dictionary mapping, all handler functions
- Used by: MCP clients calling discord_execute

**Handler Layer:**
- Purpose: Implement actual Discord API operations
- Location: `src/server.py` (lines 235-2457, ~2200 lines of handler implementations)
- Contains: 129+ async functions implementing operations across 29 categories (messages, channels, members, moderation, roles, threads, events, webhooks, automod, voice, emojis, stickers, invites, polls, audit logs, guild settings, onboarding, welcome screens, soundboards, commands, integrations, widgets, vanity URLs, templates, forum, stage, bulk operations, DM)
- Depends on: httpx for HTTP, get_headers() for auth, format_* functions for response shaping
- Used by: Execution layer through HANDLERS dispatch

**Format/Transform Layer:**
- Purpose: Shape raw Discord API responses into simplified output format
- Location: `src/server.py` (lines 26-149, format_* functions)
- Contains: 11 formatter functions (format_user, format_member, format_message, format_channel, format_role, format_event, format_invite, format_webhook, format_audit_entry, format_automod_rule)
- Depends on: Nothing (pure functions over dict data)
- Used by: Handler functions to format responses before returning to clients

**Configuration Layer:**
- Purpose: Load environment and API credentials
- Location: `src/server.py` (lines 14-21)
- Contains: Operations schema path resolution, Discord API BASE_URL, BOT_TOKEN from env, GUILD_ID from env
- Depends on: Environment variables, filesystem access to operations.json
- Used by: Server initialization and handlers

## Data Flow

**Discovery Flow (on-demand):**

1. Client calls `discord_discover()` tool
2. Tool reads OPERATIONS dict (loaded from operations.json)
3. Tool iterates through all categories and operations, building markdown text
4. Client receives human-readable category list
5. Client calls `discord_get_schema(operation)` with specific operation name
6. Tool splits operation string (e.g., "messages.send") into category and operation name
7. Tool looks up in OPERATIONS["categories"][category]["operations"][operation_name]
8. Tool returns parameter schema with types and requirements
9. Client prepares parameters and calls discord_execute

**Execution Flow:**

1. Client calls `discord_execute(operation="messages.send", params={...})`
2. discord_execute parses operation string to category.operation_name
3. discord_execute looks up handler in HANDLERS dictionary
4. discord_execute calls handler as async coroutine with params dict
5. Handler extracts required params, builds payload, constructs Discord API URL
6. Handler creates httpx.AsyncClient, makes HTTP request with auth headers
7. Handler calls resp.raise_for_status() to throw on API errors
8. Handler processes response (format_* functions or JSON dump)
9. Handler returns string result to discord_execute
10. discord_execute returns to client, or catches HTTPStatusError/Exception for error response

**State Management:**

- No state is maintained between requests
- Each handler operation is stateless: takes params, makes HTTP call, returns result
- Discord API authentication via environment variable BOT_TOKEN
- Guild context from environment variable GUILD_ID (some operations default to it)
- No caching, no local database, no session management

## Key Abstractions

**Operation:**
- Purpose: Represents a single Discord administrative capability
- Examples: `messages.send`, `members.kick`, `roles.create`
- Pattern: Dot-separated category.operation_name convention
- Location: Defined in `src/operations.json`, dispatched in `src/server.py` (lines 203-228)

**Handler:**
- Purpose: Async function that executes a single operation
- Examples: `async def handle_messages_send(params: dict) -> str`
- Pattern: Takes params dict, returns string response or raises Exception
- Location: `src/server.py` (lines 235-2457)

**Formatter:**
- Purpose: Transform raw Discord API response into simplified schema
- Examples: `def format_user(user: dict) -> dict`, `def format_member(member: dict) -> dict`
- Pattern: Pure function, dict -> dict, selects/renames fields
- Location: `src/server.py` (lines 26-149)

**HANDLERS Dictionary:**
- Purpose: Centralized operation-to-function mapping
- Examples: `"messages.send": handle_messages_send`
- Pattern: 129 mappings for all available operations
- Location: `src/server.py` (lines 2461-2620)

## Entry Points

**MCP Server Entry Point:**
- Location: `src/server.py` (lines 2623-2624)
- Triggers: Running `python -m src.server` or via MCP configuration
- Responsibilities: Initialize FastMCP instance, register three tools, start event loop

**discord_discover Tool:**
- Location: `src/server.py` (lines 156-167)
- Triggers: Client tool call "discord_discover" with no parameters
- Responsibilities: List all categories and their operations with descriptions

**discord_get_schema Tool:**
- Location: `src/server.py` (lines 170-200)
- Triggers: Client tool call "discord_get_schema" with operation parameter
- Responsibilities: Return parameter schema for a specific operation

**discord_execute Tool:**
- Location: `src/server.py` (lines 203-228)
- Triggers: Client tool call "discord_execute" with operation and params
- Responsibilities: Dispatch to handler, handle errors, return result

## Error Handling

**Strategy:** Try-catch at execution layer with API error translation

**Patterns:**

- Individual handlers call `resp.raise_for_status()` to throw on Discord API errors
- discord_execute catches `httpx.HTTPStatusError`, extracts response text and status code
- discord_execute catches generic `Exception`, converts to user-friendly error message
- Errors are returned as strings to client (no exceptions bubble up)
- Handler-specific validation: params dict key access with `.get()` for optional, direct access for required
- No validation layer: invalid parameter types caught by Discord API or cause runtime errors

Example error handling (lines 222-228):
```python
try:
    return await handler(params)
except httpx.HTTPStatusError as e:
    error_body = e.response.text
    return f"Discord API error {e.response.status_code}: {error_body}"
except Exception as e:
    return f"Error executing {operation}: {str(e)}"
```

## Cross-Cutting Concerns

**Logging:** None - no logging configured or present in codebase

**Validation:** Parameter validation happens at Discord API level
- Discord API rejects invalid types, malformed IDs, missing required fields
- No client-side schema validation before sending to API
- Schema in operations.json is informational for clients, not enforced server-side

**Authentication:** Bot token in Authorization header
- `get_headers(reason=None)` function (lines 26-34) constructs auth headers
- BOT_TOKEN loaded from environment variable on startup
- X-Audit-Log-Reason header optionally included for moderation actions
- No token refresh logic (bot token is long-lived)

**Async/Concurrency:** All handlers are async functions using httpx.AsyncClient
- Each handler creates new AsyncClient instance (not connection pooled)
- Handlers awaited by discord_execute
- FastMCP framework handles concurrency for multiple client calls

---

*Architecture analysis: 2026-01-23*
