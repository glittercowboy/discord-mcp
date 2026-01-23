# Codebase Concerns

**Analysis Date:** 2026-01-23

## Tech Debt

**Monolithic Server File:**
- Issue: All 128 Discord operations crammed into single `server.py` file (2624 lines). Duplicated handler patterns, formatting functions, and error logic throughout.
- Files: `src/server.py`
- Impact: Extremely difficult to maintain, test, or modify. Changes to error handling or formatting require updates across ~129 handler functions. Navigation is painful. No code reuse despite identical patterns.
- Fix approach: Split into separate modules by category (messages, moderation, roles, etc.). Extract common patterns into utilities. Use a handler factory pattern to reduce duplication. Current one-file approach will become unmaintainable as operations grow.

**Inconsistent Parameter Access:**
- Issue: Mix of unsafe direct dictionary access (`params["key"]`) and safe access (`params.get("key")`). No validation layer.
- Files: `src/server.py` (lines 237-403 and throughout)
- Impact: KeyError crashes when required parameters are missing. No type checking or bounds validation (e.g., message limits default to 50 but allow "up to 100").
- Fix approach: Create a centralized parameter validator that runs before handlers. Use dataclass or Pydantic models for each operation. Validate types, required fields, and constraints upfront.

**Identical Error Handling Repeated 129 Times:**
- Issue: Every handler wraps API calls in `resp.raise_for_status()` without context. Central `discord_execute` catches HTTP errors and exceptions but handler-level calls don't benefit from it.
- Files: `src/server.py` (lines 250, 265, 280, 293... repeated ~100+ times)
- Impact: Error messages don't indicate which operation failed. No retry logic. Rate limit responses aren't distinguished from permission errors. No audit trail of failures.
- Fix approach: Create a wrapper function `api_call(method, url, **kwargs)` that handles errors with context, rate limits, and logging. Replace all direct `client.post/get/patch/delete` calls with this wrapper.

## Security Considerations

**Environment Variable Not Validated at Startup:**
- Risk: Missing `DISCORD_BOT_TOKEN` or `DISCORD_GUILD_ID` silently defaults to empty string, causing cryptic API errors later
- Files: `src/server.py` (lines 20-21)
- Current mitigation: None. Bot token is silently "" if unset.
- Recommendations: Validate environment variables at startup. Raise clear error if either is missing. Check token format validity. Add logging of which guild is being accessed (without exposing token).

**No Input Sanitization for Audit Log Reasons:**
- Risk: User-provided audit log reason passed directly to Discord API without length validation or injection checks
- Files: `src/server.py` (line 33: `get_headers()` function)
- Current mitigation: None
- Recommendations: Validate reason strings. Discord has a 512-character limit. Add early validation and truncation.

**Unrestricted Webhook Message Sending:**
- Risk: `handle_webhooks_send()` accepts arbitrary webhook URL and sends payloads to it. No validation that URL belongs to the guild.
- Files: `src/server.py` (lines 1529-1543)
- Current mitigation: None
- Recommendations: Validate webhook URL origin or fetch webhook metadata first to confirm it belongs to the guild. Prevent cross-guild webhook exploitation.

**Image Download Without Size Limits:**
- Risk: `handle_emojis_create()` downloads images from arbitrary URLs with no size restrictions before base64 encoding
- Files: `src/server.py` (lines 1608-1628, specifically line 1614)
- Current mitigation: None
- Recommendations: Set max file size limit (Discord emoji limit is ~256KB). Add timeout to image downloads. Validate image format before encoding.

**Generic Exception Catching Masks Real Errors:**
- Risk: Line 227 catches all exceptions, hiding programming errors, timeouts, and connection issues under same generic message
- Files: `src/server.py` (lines 222-228)
- Current mitigation: None
- Recommendations: Catch specific exceptions (httpx.TimeoutException, ValueError, etc.) with distinct messages. Let unexpected errors surface.

## Performance Bottlenecks

**No Connection Pooling:**
- Problem: Every API call creates new `AsyncClient()` instance, initializes TLS, etc. Wasteful for consecutive calls.
- Files: `src/server.py` (line 244 and every handler creates new client)
- Cause: Pattern `async with httpx.AsyncClient() as client:` in each handler instead of reusing single client.
- Improvement path: Create module-level client instance. Handle graceful shutdown with lifespan context. Reuse for all API calls.

**No Rate Limit Handling:**
- Problem: Discord rate limits enforced with 429 responses. Server doesn't retry with backoff.
- Files: `src/server.py` (lines 224-228 don't distinguish 429 from other HTTP errors)
- Cause: All HTTP errors treated identically. No extraction of `Retry-After` header.
- Improvement path: Check response headers for rate limit info. Implement exponential backoff. Return retry information to caller.

**Large Message Listing Inefficient:**
- Problem: `handle_messages_list()` retrieves full message objects but only formats subset of fields
- Files: `src/server.py` (lines 255-268)
- Cause: No pagination or filtering on API side. Formats all returned messages then returns large JSON.
- Improvement path: Use Discord's API parameters for filtering (before_id, after_id). Implement pagination. Return only essential fields by default.

## Fragile Areas

**Emoji Parameter Edge Cases:**
- Files: `src/server.py` (lines 1608-1628)
- Why fragile: Discord has strict emoji naming rules (alphanumeric + underscore only). No validation before sending to API. Image content-type detection fragile (relies on HTTP header).
- Safe modification: Add emoji name validation regex before API call. Add image format validation (magic bytes check, not just header). Test with various image types.
- Test coverage: No tests for invalid emoji names or malformed images visible in repo.

**Member Role Management Without Hierarchy Check:**
- Files: `src/server.py` (lines ~750-800 estimated for role handlers)
- Why fragile: Discord enforces bot role hierarchy - bot can't assign roles higher than its own role. No upfront check, only API error.
- Safe modification: Before assigning roles, verify bot's highest role is above target role. Cache guild role hierarchy.
- Test coverage: No validation of role positions before API call.

**Pagination Incomplete or Missing:**
- Files: `src/server.py` (lines 255-268, 1583-1592, etc. for list operations)
- Why fragile: `limit` parameter capped at 100 but doesn't prevent requesting massive lists when offset is supported. No cursor-based pagination.
- Safe modification: Implement proper pagination with cursor/after_id. Document limits clearly.
- Test coverage: Gap on large list operations.

**Timestamp Handling with No Timezone Validation:**
- Files: `src/server.py` (imported `datetime, timedelta, timezone` at line 6 but timezone not used in event creation)
- Why fragile: Events created with start times but no validation that times are in future, valid ISO format, etc.
- Safe modification: Validate event times are future-dated, properly formatted, within Discord's allowed range.
- Test coverage: No validation of malformed timestamps.

## Test Coverage Gaps

**No Unit Tests Visible:**
- What's not tested: All 129 handler functions lack test coverage
- Files: `src/server.py` (entire codebase)
- Risk: Any change to parameter handling, formatting, or error messages could break silently
- Priority: High

**No Integration Tests:**
- What's not tested: Actual Discord API interactions
- Files: No test directory visible
- Risk: Breaking changes from Discord API updates won't be caught until user reports
- Priority: High

**No Error Scenario Testing:**
- What's not tested: 401 (unauthorized), 403 (forbidden), 404 (not found), 429 (rate limited) responses
- Files: `src/server.py` (lines 224-228 catch all but never tested)
- Risk: Error handling logic is untested guess work
- Priority: Medium

**Parameter Validation Not Tested:**
- What's not tested: Missing required parameters, invalid types, out-of-range values
- Files: All handlers rely on direct dictionary access without guards
- Risk: KeyError or type errors will surface in production
- Priority: High

## Scaling Limits

**Single GUILD_ID Hardcoded:**
- Current capacity: Only one Discord server can be managed at a time
- Limit: Configuration requires bot token + guild ID. No multi-guild support.
- Scaling path: Extend `discord_execute()` to accept guild_id in params. Store guild mappings. Support token rotation for different bots.

**No Async Queue for Bulk Operations:**
- Current capacity: Bulk delete, bulk ban run sequentially without concurrency control
- Limit: Large bulk operations (100+ items) will be slow. No backpressure handling.
- Scaling path: Implement async batch processing with configurable concurrency limits.

**Unbounded Handler Registry:**
- Current capacity: 129 handlers in dict. Each requires manual registry entry.
- Limit: Adding new operations requires modifying central HANDLERS dict and server.py
- Scaling path: Use handler discovery pattern (auto-register handlers by naming convention).

## Dependencies at Risk

**httpx Library Choice Without Fallback:**
- Risk: Custom AsyncClient code in every handler. If httpx has breaking changes, all handlers affected.
- Impact: Version upgrades require careful testing across all operations
- Migration plan: Wrap httpx behind Discord client abstraction layer. Easier to swap libraries or handle version incompatibilities.

**MCP FastMCP Framework Minimal Error Contract:**
- Risk: FastMCP tool return type is `str`. No structured error responses. All errors become text messages.
- Impact: Claude can't distinguish error types or retry intelligently
- Migration plan: (Limited by FastMCP itself) Document error response formats. Use JSON in string responses for structured errors.

**No Version Pinning in pyproject.toml:**
- Risk: `httpx>=0.28.1` and `mcp[cli]>=1.25.0` allow breaking changes on minor upgrades
- Impact: CI breaks or production deploys have surprises
- Migration plan: Pin to specific versions after testing (e.g., httpx==0.28.1, mcp==1.25.0). Use renovate/dependabot for updates.

## Missing Critical Features

**No Logging or Observability:**
- Problem: All operations silent. No audit trail of what Claude asked the bot to do. No timestamps of API calls.
- Blocks: Debugging production issues. Understanding bot usage patterns. Compliance/audit trails.

**No Request/Response Caching:**
- Problem: Same data (channel list, role list, member list) fetched fresh each time.
- Blocks: Efficient repeated operations. Reducing API load.

**No Transaction Support for Multi-Step Operations:**
- Problem: Complex operations (create role + assign to users) aren't atomic. Partial failures leave bot in inconsistent state.
- Blocks: Safe complex orchestrations.

**No Voice State Tracking:**
- Problem: Can move members to voice channels but can't query current voice state.
- Blocks: Building voice-based automation.

---

*Concerns audit: 2026-01-23*
