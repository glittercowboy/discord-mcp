# Technology Stack

**Project:** GSD Guardian (Discord Security Bot)
**Researched:** 2026-01-23
**Overall Confidence:** HIGH

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **discord.py** | 2.6.4+ | Gateway WebSocket & Discord API | Official, actively maintained, comprehensive Discord bot framework. Latest version (2.6.4 released Oct 2025) includes Components v2, modal enhancements, and voice rewrite. Python 3.8+ compatible. |
| **Python** | 3.12 | Runtime | Matches existing discord-mcp codebase. Modern async/await support, type hints, pattern matching. |
| **asyncio** | stdlib | Async runtime | Native Python async framework. discord.py built on top of it. Zero additional dependencies. |

**Confidence:** HIGH - Verified via PyPI (2.6.4 release), official GitHub repo, official documentation.

**Rationale:** discord.py is the dominant Python Discord library with 15.9k stars, 423 contributors, and active development. Handles Gateway WebSocket connections, rate limiting, intents, and all Discord API operations. The 2.x series includes major improvements: slash commands, buttons/modals, voice connection rewrite, poll support, and username system migration.

### HTTP Client (Shared with discord-mcp)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **httpx** | 0.28.1+ | HTTP client for REST APIs | Already used in discord-mcp. Async-first, HTTP/2 support, connection pooling. Needed for external API calls (URL scanning, etc). |

**Confidence:** HIGH - Already in pyproject.toml dependencies.

**Rationale:** Maintains consistency with existing codebase. While discord.py handles Discord API internally, Guardian needs httpx for external services (VirusTotal, URLScan, etc).

### Configuration Management
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pydantic-settings** | 2.x | Environment variables & config | Type-safe configuration with validation. FastAPI-recommended. Integrates seamlessly with Pydantic models. Simple .env file support. |
| **python-dotenv** | 1.0+ | .env file loading | Development convenience. Load environment variables from .env for local testing. |

**Confidence:** HIGH - pydantic-settings is the 2026 standard for type-safe config in Python.

**Rationale:** pydantic-settings provides type safety, validation, and declarative configuration. Better fit than Dynaconf for this project because:
- Guardian has straightforward config needs (tokens, thresholds, channel IDs)
- Type safety prevents runtime config errors
- Already Pydantic-heavy if using FastMCP patterns
- No need for Dynaconf's multi-layer/dynamic loading complexity

### Structured Logging
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **loguru** | 0.7+ | Structured logging | Production-grade logging with zero boilerplate. JSON serialization, async-safe, exception handling, non-blocking sinks. Simpler API than structlog. |

**Confidence:** HIGH - Industry standard for modern Python logging in 2026.

**Rationale:** Loguru recommended over stdlib logging or structlog because:
- Zero configuration required (vs stdlib's complexity)
- Async-safe by default (critical for discord.py event handlers)
- Structured JSON output for Railway logs
- Automatic exception capture with full context
- Simpler API than structlog for single-developer projects

### Security & Moderation
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **virustotal-python** | 1.0+ | URL scanning API client | Official VirusTotal v3 API wrapper. Rate limiting, bulk scanning, CSV export. |

**Confidence:** MEDIUM - PyPI package exists, widely used, but version info from WebSearch only.

**Rationale:** For link scanner feature. VirusTotal provides comprehensive malware/phishing detection across 70+ antivirus engines. Alternative: URLScan.io (requires separate client). VirusTotal chosen for broader coverage and mature Python SDK.

### Development & Testing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pytest** | 8.x | Test framework | Industry standard. Excellent async support via pytest-asyncio. |
| **pytest-asyncio** | 0.24+ | Async test support | Essential for testing discord.py async handlers and event loops. |
| **dpytest** | 0.7+ | Discord.py testing | Dedicated library for mocking Discord API, testing commands, events. |
| **ruff** | 0.8+ | Linting & formatting | Fastest Python linter (Rust-based). Combines flake8, isort, black functionality. |
| **mypy** | 1.13+ | Type checking | Static type checking for Python. Catches type errors at development time. |

**Confidence:** HIGH - Standard Python development tools in 2026.

**Rationale:**
- pytest + pytest-asyncio: Standard async testing stack
- dpytest: Discord-specific testing (mocks bot interactions without real Discord connection)
- ruff: 10-100x faster than traditional tools, single tool for linting + formatting
- mypy: Type safety beyond Pydantic, catches logic errors early

### Package Management
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **uv** | latest | Python package & environment manager | 10-100x faster than pip/Poetry. Manages Python versions, dependencies, virtualenvs. Written in Rust. |

**Confidence:** MEDIUM - Rapidly growing adoption in 2025-2026, but newer than Poetry/pip-tools.

**Rationale:** uv replaces pip, pip-tools, poetry, pyenv, virtualenv in one tool. For this brownfield project:
- **Pros:** Blazing fast installs, manages Python versions, creates venvs 80x faster
- **Cons:** Newer ecosystem (though maturing fast in 2025-2026)
- **Decision:** Recommended for new Guardian component. Can coexist with existing discord-mcp setup.

**Fallback:** If uv adoption is blocked, use pip-tools (requirements.in → requirements.txt) for reproducible builds.

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Railway** | N/A | Hosting platform | Already specified in project requirements. Zero-config deploys, 24/7 uptime, GitHub integration, environment variable management. |

**Confidence:** HIGH - Specified in project context.

**Rationale:** Railway provides:
- Worker process support (Guardian runs as separate worker from discord-mcp)
- Automatic restarts on crashes
- Environment variable management via UI
- GitHub auto-deploy on push
- Free tier sufficient for single-server bot

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Discord Library | discord.py | pycord, disnake, nextcord | discord.py resumed active development after 2021 hiatus. Most mature, best documented, largest community. Pycord/disnake/nextcord are forks from when dpy was archived; discord.py now superior. |
| Config Management | pydantic-settings | dynaconf | Dynaconf is overkill for Guardian's straightforward config needs. Pydantic-settings provides sufficient type safety and validation without multi-layer complexity. |
| Logging | loguru | structlog, stdlib logging | Loguru simpler API than structlog, better async support than stdlib. Production-grade without boilerplate. |
| Package Manager | uv | poetry, pip-tools | Poetry mature but slower. pip-tools doesn't manage Python versions. uv fastest, most comprehensive. Risk: newer tool (mitigated by rapid 2025-2026 adoption). |
| Testing | dpytest | distest, manual mocking | dpytest most mature Discord.py testing library. distest less maintained. Manual mocking too much boilerplate. |

## What NOT to Use

| Technology | Why Avoid |
|------------|-----------|
| **discord.js** | Wrong language. Project is Python. Switching languages for Guardian creates deployment/maintenance complexity. |
| **selfcord / discord.py-self** | Violates Discord ToS. These libraries enable userbots (automating user accounts). Use official bot API only. |
| **synchronous HTTP libraries (requests)** | Blocks event loop. discord.py is async; blocking calls cause Gateway disconnects. Use httpx or aiohttp. |
| **Global state for config** | Use pydantic-settings for type-safe config injection. Global variables cause testing difficulties and race conditions. |
| **threading for concurrency** | discord.py uses asyncio. Mixing threads + async creates complexity. Use asyncio.create_task() instead. |

## Installation

### Core Dependencies

```bash
# Using uv (recommended)
uv venv
uv pip install discord.py>=2.6.4 httpx>=0.28.1 pydantic-settings>=2.0 python-dotenv>=1.0 loguru>=0.7 virustotal-python>=1.0

# Using pip (fallback)
python3.12 -m venv .venv
source .venv/bin/activate
pip install discord.py>=2.6.4 httpx>=0.28.1 pydantic-settings>=2.0 python-dotenv>=1.0 loguru>=0.7 virustotal-python>=1.0
```

### Development Dependencies

```bash
# Using uv
uv pip install pytest>=8.0 pytest-asyncio>=0.24 dpytest>=0.7 ruff>=0.8 mypy>=1.13

# Using pip
pip install pytest>=8.0 pytest-asyncio>=0.24 dpytest>=0.7 ruff>=0.8 mypy>=1.13
```

### pyproject.toml Addition

```toml
[project]
dependencies = [
    "discord.py>=2.6.4",
    "httpx>=0.28.1",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0",
    "loguru>=0.7",
    "virustotal-python>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "dpytest>=0.7",
    "ruff>=0.8",
    "mypy>=1.13",
]
```

## Integration with Existing discord-mcp

Guardian runs as a **separate worker process** alongside discord-mcp:

| Component | Type | Purpose | Stack |
|-----------|------|---------|-------|
| **discord-mcp** | MCP Server | REST API operations for Claude | FastMCP, httpx, Python 3.12 |
| **Guardian** | Discord Bot | Real-time security via Gateway | discord.py, httpx, Python 3.12 |

**Shared:**
- Python 3.12 runtime
- httpx for external HTTP calls
- Railway deployment
- Environment variables for tokens

**Separate:**
- discord-mcp: No Gateway connection (stateless REST)
- Guardian: Persistent Gateway WebSocket (24/7 event loop)

**Deployment Strategy:**
1. Extend existing pyproject.toml with discord.py + Guardian dependencies
2. Create `guardian/` module alongside discord-mcp code
3. Add Procfile entry: `worker: python -m guardian.main`
4. Railway runs both processes: MCP server + Guardian worker

## Version Pinning Strategy

**Pin major+minor, allow patch:**
- `discord.py>=2.6.0,<2.7` - Stable API within 2.6.x series
- `httpx>=0.28.0,<0.29` - HTTP/2 support stable in 0.28.x
- `pydantic-settings>=2.0,<3.0` - v2 API stable

**Rationale:** Allows security patches without breaking changes. Review major version upgrades manually.

## Sources

### HIGH Confidence (Official Documentation)
- [discord.py PyPI - Version 2.6.4](https://pypi.org/project/discord.py/)
- [discord.py GitHub Repository](https://github.com/Rapptz/discord.py)
- [discord.py Changelog - Version 2.6 Features](https://discordpy.readthedocs.io/en/latest/whats_new.html)
- [discord.py API Reference](https://discordpy.readthedocs.io/en/stable/api.html)
- [FastAPI Settings Management (pydantic-settings)](https://fastapi.tiangolo.com/advanced/settings/)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

### MEDIUM Confidence (Verified Community Sources)
- [Better Stack: Best Python Logging Libraries](https://betterstack.com/community/guides/logging/best-python-logging-libraries/)
- [Loguru GitHub](https://github.com/Delgan/loguru)
- [uv vs Poetry Comparison 2025](https://medium.com/@hitorunajp/poetry-vs-uv-which-python-package-manager-should-you-use-in-2025-4212cb5e0a14)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Railway Discord Bot Deployment Guide](https://daily-dev-tips.com/posts/hosting-a-discord-bot-on-railway/)
- [Railway Discord.py Template](https://github.com/railwayapp-templates/discordpy-bot)
- [dpytest Documentation](https://dpytest.readthedocs.io/en/latest/tutorials/getting_started.html)
- [pytest-asyncio Best Practices](https://krython.com/tutorial/python/testing-async-code-pytest-asyncio/)
- [Python Discord Bot Testing Guide](https://github.com/python-discord/bot/blob/main/tests/README.md)

### LOW Confidence (Unverified, Flagged for Validation)
- virustotal-python version number (needs PyPI verification)
- dpytest version 0.7+ (needs official docs verification)
