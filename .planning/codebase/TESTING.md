# Testing Patterns

**Analysis Date:** 2026-01-23

## Test Framework

**Runner:**
- No test framework detected (pytest, unittest, nose not in dependencies)
- `pyproject.toml` contains only runtime dependencies: `httpx>=0.28.1`, `mcp[cli]>=1.25.0`

**Assertion Library:**
- Not applicable - no testing framework in use

**Run Commands:**
- No test command configured in `pyproject.toml`
- Manual testing only via running the MCP server: `if __name__ == "__main__": mcp.run()`

## Test File Organization

**Location:**
- No test files present in codebase
- No `tests/`, `test/`, or `spec/` directories
- All test discovery patterns return no matches (Glob search for `*.test.ts`, `*.spec.ts`, `test_*.py`, `*_test.py`)

**Naming:**
- Not applicable - no tests in codebase

**Structure:**
- Not applicable - no tests in codebase

## Test Structure

**Suite Organization:**
- Not implemented

**Patterns:**
- Not implemented

## Mocking

**Framework:**
- Not applicable - no testing framework in use

**Patterns:**
- Not applicable

**What to Mock:**
- Not documented (would need httpx, Discord API responses)

**What NOT to Mock:**
- Not documented

## Fixtures and Factories

**Test Data:**
- Not applicable - no test fixtures present

**Location:**
- Not applicable

## Coverage

**Requirements:** Not enforced

**View Coverage:**
- No coverage tool configured

## Test Types

**Unit Tests:**
- Not implemented
- Would need to test: formatter functions (`format_user`, `format_member`, etc.), parameter validation in `discord_get_schema`

**Integration Tests:**
- Not implemented
- Would need to test: Discord API integration with real or mocked httpx calls

**E2E Tests:**
- Not implemented
- Could test via MCP server running with test Discord guild

## Common Patterns

**Async Testing:**
- Not implemented
- Handlers are async functions decorated with `@mcp.tool()`, would require async test framework

**Error Testing:**
- Not implemented
- Error handling in `discord_execute` (lines 222-228) catches `httpx.HTTPStatusError` and generic `Exception`
- Pattern that could be tested:
```python
try:
    return await handler(params)
except httpx.HTTPStatusError as e:
    error_body = e.response.text
    return f"Discord API error {e.response.status_code}: {error_body}"
except Exception as e:
    return f"Error executing {operation}: {str(e)}"
```

## Current State

**Testing Infrastructure:** None

The Discord MCP server has no automated test suite. All validation occurs at runtime:

1. **Parameter validation** in `discord_get_schema` (lines 177-200):
   - Checks operation format: `"category.operation"`
   - Validates category exists
   - Validates operation exists in category
   - Returns schema with required/optional indicators

2. **Handler validation** in `discord_execute` (lines 204-228):
   - Checks operation format
   - Verifies handler exists in HANDLERS dict
   - Catches HTTP errors and generic exceptions
   - Returns human-readable error messages

3. **Data formatting** via formatter functions (lines 37-148):
   - `format_user`, `format_member`, `format_message`, `format_channel`, `format_role`
   - `format_event`, `format_invite`, `format_webhook`, `format_audit_entry`, `format_automod_rule`
   - Extract essential fields from Discord API responses
   - Use `.get()` with defaults for safe access to optional fields

**No test coverage exists for:**
- HTTP request/response handling
- Parameter extraction from Discord API responses
- Edge cases in formatter functions
- Formatter functions with missing/malformed data
- Discord API error scenarios
- Token/credential validation
- HANDLERS dictionary completeness against operations.json

---

*Testing analysis: 2026-01-23*
