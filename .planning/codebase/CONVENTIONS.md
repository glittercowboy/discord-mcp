# Coding Conventions

**Analysis Date:** 2026-01-23

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `server.py`, `operations.json`
- Package structure uses `__init__.py` for package markers
- Data files use descriptive snake_case names

**Functions:**
- All handler functions use `handle_` prefix followed by category and operation: `handle_messages_send`, `handle_members_list`, `handle_automod_edit`
- Utility formatter functions use `format_` prefix: `format_user`, `format_member`, `format_message`, `format_channel`, `format_role`, `format_event`, `format_invite`, `format_webhook`, `format_audit_entry`, `format_automod_rule`
- Regular utility functions use simple descriptive names: `get_headers`, `discord_discover`, `discord_get_schema`, `discord_execute`
- Async functions are prefixed with `async def` and typically are handlers or main operations

**Variables:**
- Local variables use snake_case: `channel_id`, `message_id`, `user_id`, `payload`, `response`, `formatted`
- Constants use UPPER_SNAKE_CASE: `BASE_URL`, `BOT_TOKEN`, `GUILD_ID`, `OPERATIONS`, `OPERATIONS_PATH`, `HANDLERS`
- Dictionary keys follow snake_case: `channel_id`, `message_id`, `global_name`, `display_name`, `joined_at`

**Types:**
- Type hints use lowercase `dict` with optional generic types when documented
- Return type annotations are consistently applied: `-> dict`, `-> str`
- Parameter annotations use base types: `params: dict`, `operation: str`, `reason: str = None`

## Code Style

**Formatting:**
- No explicit formatter configured (ruff, black, isort not found in dependencies)
- Line length appears flexible but handlers typically span 10-30 lines
- Indentation: 4 spaces (Python standard)
- Blank lines: 2 lines between section headers (see header pattern), 1-2 lines between function definitions

**Linting:**
- No explicit linting configuration detected (no ruff.toml, setup.cfg, .flake8)
- Code follows standard Python conventions implicitly
- No style checking enforced at development time

**Section Organization:**
- Code is organized into logical sections marked with headers using `# ============================================================================`
- Major sections: imports, configuration, META-TOOLS, MESSAGE HANDLERS, REACTION HANDLERS, THREAD HANDLERS, CHANNEL HANDLERS, MEMBER HANDLERS, MODERATION HANDLERS, ROLE HANDLERS, INVITE HANDLERS, EVENTS HANDLERS, POLLS HANDLERS, GUILD HANDLERS, AUDIT LOG HANDLERS, AUTOMOD HANDLERS, WEBHOOK HANDLERS, VOICE HANDLERS, EMOJI HANDLERS, STICKER HANDLERS, FORUM HANDLERS, STAGE HANDLERS, ONBOARDING HANDLERS, WELCOME SCREEN HANDLERS, SOUNDBOARD HANDLERS, COMMAND HANDLERS, INTEGRATION HANDLERS, WIDGET HANDLERS, VANITY HANDLERS, TEMPLATES HANDLERS, DM HANDLERS, BULK BAN HANDLERS

## Import Organization

**Order:**
1. Standard library imports (datetime, pathlib, urllib.parse, base64, json, os)
2. Third-party imports (httpx, mcp.server.fastmcp)

**Pattern from `src/server.py` lines 3-11:**
```python
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP
```

**Path Aliases:**
- Not used in this codebase
- All imports are absolute references

## Error Handling

**Patterns:**
- HTTP errors are caught explicitly: `except httpx.HTTPStatusError as e:` (lines 224-226)
- Generic exceptions are caught as fallback: `except Exception as e:`
- Error messages include context: `f"Discord API error {e.response.status_code}: {error_body}"`
- `resp.raise_for_status()` is called after every HTTP request to propagate non-200 responses as exceptions
- No try-except in individual handlers (error handling centralized in `discord_execute`)

**Error Response Pattern:**
- All handlers return string messages: success cases return `f"Operation result: {details}"`, error cases are caught and formatted at the top level

## Logging

**Framework:** No explicit logging framework

**Patterns:**
- No logging statements found in codebase
- Debugging relies on return strings
- All status/result information is returned as string responses
- Console output would happen only through `raise` or unhandled exceptions

## Comments

**When to Comment:**
- Section headers use comment blocks with visual separators (80 char line with equals signs)
- Sparse inline comments observed
- Comments typically explain intent at section level, not line level

**JSDoc/Docstrings:**
- Google-style docstrings used on public functions
- Three-quote docstrings on all `@mcp.tool()` decorated functions
- Example from line 171-176:
```python
def discord_get_schema(operation: str) -> str:
    """Get detailed parameter schema for a specific operation.

    Args:
        operation: Operation identifier (e.g., 'messages.send', 'members.list')
    """
```

**Formatter Function Documentation:**
- Formatter functions have one-line docstrings: `"""Format user object with essential fields."""`

## Function Design

**Size:**
- Handler functions are typically 10-25 lines
- Most handlers follow same pattern: extract params, build HTTP request, execute, return result
- Example from `handle_messages_send` (lines 236-252): 16 lines

**Parameters:**
- All handlers accept single `params: dict` parameter
- No type-checking on params (parameters validated at operation discovery level in `discord_get_schema`)
- Optional parameters checked with `.get()` method

**Return Values:**
- Async handlers always return strings
- Success messages: `f"Resource operation (ID: {id})"` or `json.dumps(formatted_list, indent=2)`
- Error messages propagated from exception handlers
- No None returns observed

## Module Design

**Exports:**
- No explicit `__all__` export lists
- Public functions: formatter functions, handler functions (bound to HANDLERS dict)
- `@mcp.tool()` decorator on discovery functions makes them public to MCP framework
- Handler functions accessed through HANDLERS dict mapping at module end (lines ~1750+)

**Barrel Files:**
- `src/__init__.py` is minimal (2 lines, empty module)
- No re-exports or convenience imports

**Handler Registration Pattern:**
- All handler functions defined in module scope
- HANDLERS dictionary created near end of file mapping operation names to functions
- Example pattern:
```python
HANDLERS = {
    "messages.send": handle_messages_send,
    "messages.list": handle_messages_list,
    # ... etc
}
```

---

*Convention analysis: 2026-01-23*
