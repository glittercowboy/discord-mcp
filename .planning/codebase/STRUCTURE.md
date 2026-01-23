# Codebase Structure

**Analysis Date:** 2026-01-23

## Directory Layout

```
discord-mcp/
├── src/                    # Main source code directory
│   ├── __init__.py         # Package marker (minimal content)
│   ├── server.py           # Core MCP server (2624 lines)
│   └── operations.json     # Operation definitions (1040 lines, 29 categories)
├── .venv/                  # Python virtual environment (generated)
├── .planning/              # GSD planning directory
│   └── codebase/           # Codebase analysis documents
├── .git/                   # Git repository
├── .gitignore              # Git exclusions (bytecode, env files)
├── .python-version         # Python 3.12
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Dependency lock file
├── LICENSE                 # MIT license
├── README.md               # Comprehensive setup and usage guide
└── GUARDIAN-BRIEF.md       # Project brief document
```

## Directory Purposes

**src/**
- Purpose: All runnable source code for the MCP server
- Contains: Python modules (server.py, __init__.py) and operation definitions (operations.json)
- Key files: `server.py` (implementation), `operations.json` (schema)

**.planning/codebase/**
- Purpose: GSD (Guardian/Strategic Development) analysis documents
- Contains: Architecture and structure analysis documents
- Key files: ARCHITECTURE.md, STRUCTURE.md, and potentially STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**.venv/**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (in .gitignore)

**.git/**
- Purpose: Git version control
- Generated: Yes
- Committed: N/A (version control folder)

## Key File Locations

**Entry Points:**
- `src/server.py` (lines 2623-2624): Main entry point - initializes FastMCP and starts server
- `src/__init__.py`: Package marker, no active code

**Configuration:**
- `pyproject.toml`: Project name, version, dependencies (httpx, mcp[cli])
- `.python-version`: Python 3.12 requirement
- `src/server.py` (lines 14-21): Runtime config loading (BOT_TOKEN, GUILD_ID from environment)

**Core Logic:**
- `src/server.py` (lines 156-167): discord_discover tool - list available operations
- `src/server.py` (lines 170-200): discord_get_schema tool - get operation parameter schema
- `src/server.py` (lines 203-228): discord_execute tool - execute operations with routing
- `src/server.py` (lines 235-2457): Handler implementations (129 async functions organized by category)

**Operation Definitions:**
- `src/operations.json`: Complete operation schema with 29 categories, 128 operations, parameter definitions

**Utilities:**
- `src/server.py` (lines 26-34): get_headers() - construct Discord API auth headers
- `src/server.py` (lines 37-149): format_* functions - transform Discord API responses (11 formatters)

**Testing:**
- Not present - no test files in codebase

**Documentation:**
- `README.md`: Setup instructions, Discord bot creation, installation
- `LICENSE`: MIT license
- `GUARDIAN-BRIEF.md`: Project brief document

## Naming Conventions

**Files:**
- `server.py`: Main server module (standard Python convention)
- `operations.json`: Operation schema (standard JSON config)
- `__init__.py`: Python package marker (required)

**Directories:**
- `src/`: Source code (lowercase, conventional)
- `.venv/`: Virtual environment (dotfile prefix)
- `.planning/`: Planning directory (dotfile prefix)
- `codebase/`: Sub-directory for analysis docs

**Functions:**
- `handle_CATEGORY_OPERATION()`: Handler functions follow category_operation pattern
  - Examples: `handle_messages_send`, `handle_members_kick`, `handle_roles_create`
  - All async functions (declared with `async def`)
  - All take single `params: dict` parameter
  - All return `str` (response or error message)

- `format_ENTITY()`: Formatter functions follow entity naming
  - Examples: `format_user`, `format_member`, `format_message`, `format_channel`
  - Pure functions (no side effects)
  - Transform Discord API response dicts to simplified output format

- Utilities: `get_headers()` - prefix-less, generic naming

**Variables:**
- `BASE_URL`: Constant, uppercase
- `BOT_TOKEN`, `GUILD_ID`: Environment-sourced constants, uppercase
- `OPERATIONS`: Loaded schema dict, uppercase (constant)
- `HANDLERS`: Mapping dict, uppercase (constant)
- `mcp`: FastMCP instance, lowercase (convention)
- `params`, `headers`, `payload`: function-local, lowercase
- `channel_id`, `message_id`, `user_id`: underscore-separated IDs

**Types:**
- `dict`: Used throughout for flexible parameter passing and API responses
- `str`: Return type for all tools and handlers (results serialized as strings)
- `list`: For arrays (message IDs, roles, etc.)

## Where to Add New Code

**New Discord Operation:**

1. **Add to operation schema:**
   - Edit `src/operations.json`
   - Add to appropriate category under `"operations"` key
   - Define: operation name, description, parameters with types and requirements

2. **Implement handler:**
   - Add async function to `src/server.py`
   - Location: Group with related handlers (messages with messages, channels with channels, etc.)
   - Naming: `async def handle_CATEGORY_OPERATION(params: dict) -> str:`
   - Implementation: Extract params → build payload → make httpx call → format response

3. **Register handler:**
   - Add mapping to HANDLERS dict in `src/server.py` (lines 2461-2620)
   - Format: `"category.operation": handle_category_operation,`

**New Formatter:**
- Location: `src/server.py`, group with other formatters (lines 37-149)
- Naming: `def format_ENTITY(entity: dict) -> dict:`
- Pattern: Extract key fields from raw Discord API response, return simplified dict
- Used by: Handlers that need to format responses

**Utilities/Helpers:**
- Location: `src/server.py`, near top after imports but before tools/handlers
- Keep stateless, pure functions
- If reused across handlers, place in utilities section

**Integration Points:**
- Discord API v10: Change BASE_URL in line 19 if API version updates
- Authentication: get_headers() function handles auth header construction (line 26)
- Response formatting: Use format_* functions for consistency

## Special Directories

**.planning/codebase/**
- Purpose: GSD analysis documents (generated by mapper, consumed by planner/executor)
- Generated: Yes (by Claude mapper tool)
- Committed: Yes (part of repository)

**.venv/site-packages/**
- Purpose: Installed Python packages (httpx, mcp, dependencies)
- Generated: Yes (by `uv sync`)
- Committed: No

**src/__pycache__/**
- Purpose: Python compiled bytecode
- Generated: Yes (by Python interpreter)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-01-23*
