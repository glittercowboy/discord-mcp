"""Discord MCP Server - Full admin control over Discord communities."""

import asyncio
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

import httpx
from mcp.server.fastmcp import FastMCP

# Load operations schema
OPERATIONS_PATH = Path(__file__).parent / "operations.json"
with open(OPERATIONS_PATH) as f:
    OPERATIONS = json.load(f)

# Discord API configuration
BASE_URL = "https://discord.com/api/v10"
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")

mcp = FastMCP("discord-mcp")


def get_headers(reason: str = None) -> dict:
    """Get authorization headers for Discord API."""
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    if reason:
        headers["X-Audit-Log-Reason"] = reason
    return headers


def format_user(user: dict) -> dict:
    """Format user object with essential fields."""
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "display_name": user.get("global_name") or user.get("username"),
    }


def format_member(member: dict) -> dict:
    """Format member object with essential fields."""
    user = member.get("user", {})
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "display_name": member.get("nick") or user.get("global_name") or user.get("username"),
        "roles": member.get("roles", []),
        "joined_at": member.get("joined_at"),
    }


def format_message(msg: dict) -> dict:
    """Format message object with essential fields."""
    return {
        "id": msg.get("id"),
        "content": msg.get("content"),
        "author": format_user(msg.get("author", {})),
        "timestamp": msg.get("timestamp"),
        "reply_to": msg.get("referenced_message", {}).get("id") if msg.get("referenced_message") else None,
    }


def format_channel(channel: dict) -> dict:
    """Format channel object with essential fields."""
    return {
        "id": channel.get("id"),
        "name": channel.get("name"),
        "type": channel.get("type"),
        "topic": channel.get("topic"),
        "parent_id": channel.get("parent_id"),
    }


def format_role(role: dict) -> dict:
    """Format role object with essential fields."""
    return {
        "id": role.get("id"),
        "name": role.get("name"),
        "color": role.get("color"),
        "position": role.get("position"),
        "mentionable": role.get("mentionable"),
        "permissions": role.get("permissions"),
    }


def format_event(event: dict) -> dict:
    """Format scheduled event object."""
    return {
        "id": event.get("id"),
        "name": event.get("name"),
        "description": event.get("description"),
        "start_time": event.get("scheduled_start_time"),
        "end_time": event.get("scheduled_end_time"),
        "status": event.get("status"),
        "location": event.get("entity_metadata", {}).get("location") if event.get("entity_metadata") else None,
    }


def format_invite(invite: dict) -> dict:
    """Format invite object."""
    return {
        "code": invite.get("code"),
        "url": f"https://discord.gg/{invite.get('code')}",
        "channel": invite.get("channel", {}).get("name"),
        "inviter": format_user(invite.get("inviter", {})) if invite.get("inviter") else None,
        "uses": invite.get("uses"),
        "max_uses": invite.get("max_uses"),
        "expires_at": invite.get("expires_at"),
    }


def format_webhook(webhook: dict) -> dict:
    """Format webhook object."""
    return {
        "id": webhook.get("id"),
        "name": webhook.get("name"),
        "channel_id": webhook.get("channel_id"),
        "url": webhook.get("url"),
    }


def format_audit_entry(entry: dict) -> dict:
    """Format audit log entry."""
    return {
        "id": entry.get("id"),
        "action_type": entry.get("action_type"),
        "user_id": entry.get("user_id"),
        "target_id": entry.get("target_id"),
        "reason": entry.get("reason"),
        "changes": entry.get("changes"),
    }


def format_automod_rule(rule: dict) -> dict:
    """Format automod rule."""
    return {
        "id": rule.get("id"),
        "name": rule.get("name"),
        "enabled": rule.get("enabled"),
        "trigger_type": rule.get("trigger_type"),
        "actions": rule.get("actions"),
    }


# ============================================================================
# META-TOOLS (On-demand discovery pattern)
# ============================================================================


@mcp.tool()
def discord_discover() -> str:
    """Browse all available Discord operations organized by category."""
    lines = ["# Discord Operations\n"]
    for cat_name, cat_data in OPERATIONS["categories"].items():
        lines.append(f"## {cat_name}")
        lines.append(f"{cat_data['description']}\n")
        for op_name, op_data in cat_data["operations"].items():
            lines.append(f"- **{cat_name}.{op_name}**: {op_data['description']}")
        lines.append("")
    lines.append("\nUse `discord_get_schema` to see parameters for any operation.")
    return "\n".join(lines)


@mcp.tool()
def discord_get_schema(operation: str) -> str:
    """Get detailed parameter schema for a specific operation.

    Args:
        operation: Operation identifier (e.g., 'messages.send', 'members.list') or 'batch.category.action' for batch operations (e.g., 'batch.members.add_role')
    """
    parts = operation.split(".")

    # Handle batch operations (batch.category.action)
    if len(parts) == 3 and parts[0] == "batch":
        cat_name = "batch"
        op_name = f"{parts[1]}.{parts[2]}"
    elif len(parts) == 2:
        cat_name, op_name = parts
    else:
        return f"Invalid operation format: {operation}. Use 'category.operation' or 'batch.category.action' format."

    if cat_name not in OPERATIONS["categories"]:
        return f"Unknown category: {cat_name}. Use discord_discover to see categories."

    cat = OPERATIONS["categories"][cat_name]
    if op_name not in cat["operations"]:
        return f"Unknown operation: {op_name} in {cat_name}. Available: {list(cat['operations'].keys())}"

    op = cat["operations"][op_name]
    lines = [f"# {operation}", f"{op['description']}\n", "## Parameters"]

    params = op.get("parameters", {})
    if not params:
        lines.append("No parameters required.")
    else:
        for param_name, param_data in params.items():
            req = "required" if param_data.get("required") else "optional"
            lines.append(f"- **{param_name}** ({param_data['type']}, {req}): {param_data['description']}")

    return "\n".join(lines)


@mcp.tool()
async def discord_execute(operation: str, params: dict) -> str:
    """Execute a Discord operation with specified parameters.

    Args:
        operation: Operation identifier (e.g., 'messages.send', 'members.list') or 'batch.category.action' for batch operations
        params: Operation parameters (get schema first)
    """
    parts = operation.split(".")

    # Handle batch operations (batch.category.action)
    if len(parts) == 3 and parts[0] == "batch":
        handler_key = f"batch.{parts[1]}.{parts[2]}"
    elif len(parts) == 2:
        handler_key = f"{parts[0]}.{parts[1]}"
    else:
        return f"Invalid operation format: {operation}"

    # Route to handler
    handler = HANDLERS.get(handler_key)
    if not handler:
        return f"No handler for operation: {operation}"

    try:
        return await handler(params)
    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        return f"Discord API error {e.response.status_code}: {error_body}"
    except Exception as e:
        return f"Error executing {operation}: {str(e)}"


# ============================================================================
# MESSAGE HANDLERS
# ============================================================================


async def handle_messages_send(params: dict) -> str:
    channel_id = params["channel_id"]
    content = params["content"]

    payload = {"content": content}
    if params.get("reply_to"):
        payload["message_reference"] = {"message_id": params["reply_to"]}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/messages",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        msg = resp.json()
        return f"Message sent (ID: {msg['id']})"


async def handle_messages_list(params: dict) -> str:
    channel_id = params["channel_id"]
    limit = min(params.get("limit", 50), 100)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/messages",
            headers=get_headers(),
            params={"limit": limit},
        )
        resp.raise_for_status()
        messages = resp.json()
        formatted = [format_message(m) for m in messages]
        return json.dumps(formatted, indent=2)


async def handle_messages_get(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_message(resp.json()), indent=2)


async def handle_messages_delete(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Message {message_id} deleted"


async def handle_messages_bulk_delete(params: dict) -> str:
    channel_id = params["channel_id"]
    message_ids = params["message_ids"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/messages/bulk-delete",
            headers=get_headers(),
            json={"messages": message_ids},
        )
        resp.raise_for_status()
        return f"Deleted {len(message_ids)} messages"


async def handle_messages_edit(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]
    content = params["content"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}",
            headers=get_headers(),
            json={"content": content},
        )
        resp.raise_for_status()
        return f"Message {message_id} edited"


async def handle_messages_pin(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/channels/{channel_id}/pins/{message_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Message {message_id} pinned"


async def handle_messages_unpin(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/pins/{message_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Message {message_id} unpinned"


async def handle_messages_list_pins(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/pins",
            headers=get_headers(),
        )
        resp.raise_for_status()
        messages = resp.json()
        formatted = [format_message(m) for m in messages]
        return json.dumps(formatted, indent=2)


async def handle_messages_crosspost(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/crosspost",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Message {message_id} crossposted to following servers"


# ============================================================================
# REACTION HANDLERS
# ============================================================================


async def handle_reactions_add(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]
    emoji = quote(params["emoji"], safe="")

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Reaction {params['emoji']} added"


async def handle_reactions_remove(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]
    emoji = quote(params["emoji"], safe="")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Reaction {params['emoji']} removed"


async def handle_reactions_remove_user(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]
    emoji = quote(params["emoji"], safe="")
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Reaction {params['emoji']} removed from user {user_id}"


async def handle_reactions_remove_all(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return "All reactions removed"


async def handle_reactions_list(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]
    emoji = quote(params["emoji"], safe="")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        users = resp.json()
        formatted = [format_user(u) for u in users]
        return json.dumps(formatted, indent=2)


# ============================================================================
# THREAD HANDLERS
# ============================================================================


async def handle_threads_create(params: dict) -> str:
    channel_id = params["channel_id"]
    name = params["name"]
    message_id = params.get("message_id")
    auto_archive = params.get("auto_archive_duration", 1440)

    payload = {
        "name": name,
        "auto_archive_duration": auto_archive,
    }

    async with httpx.AsyncClient() as client:
        if message_id:
            url = f"{BASE_URL}/channels/{channel_id}/messages/{message_id}/threads"
        else:
            url = f"{BASE_URL}/channels/{channel_id}/threads"
            payload["type"] = 11  # PUBLIC_THREAD

        resp = await client.post(url, headers=get_headers(), json=payload)
        resp.raise_for_status()
        thread = resp.json()
        return f"Thread created: {thread['name']} (ID: {thread['id']})"


async def handle_threads_list(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/threads/archived/public",
            headers=get_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        threads = [{"id": t["id"], "name": t["name"]} for t in data.get("threads", [])]
        return json.dumps(threads, indent=2)


async def handle_threads_join(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/channels/{thread_id}/thread-members/@me",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Joined thread {thread_id}"


async def handle_threads_leave(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{thread_id}/thread-members/@me",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Left thread {thread_id}"


async def handle_threads_add_member(params: dict) -> str:
    thread_id = params["thread_id"]
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/channels/{thread_id}/thread-members/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Added user {user_id} to thread {thread_id}"


async def handle_threads_remove_member(params: dict) -> str:
    thread_id = params["thread_id"]
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{thread_id}/thread-members/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Removed user {user_id} from thread {thread_id}"


async def handle_threads_archive(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/channels/{thread_id}",
            headers=get_headers(),
            json={"archived": True},
        )
        resp.raise_for_status()
        return f"Thread {thread_id} archived"


async def handle_threads_unarchive(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/channels/{thread_id}",
            headers=get_headers(),
            json={"archived": False},
        )
        resp.raise_for_status()
        return f"Thread {thread_id} unarchived"


async def handle_threads_lock(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/channels/{thread_id}",
            headers=get_headers(),
            json={"locked": True},
        )
        resp.raise_for_status()
        return f"Thread {thread_id} locked"


async def handle_threads_delete(params: dict) -> str:
    thread_id = params["thread_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{thread_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Thread {thread_id} deleted"


async def handle_threads_list_members(params: dict) -> str:
    thread_id = params["thread_id"]
    limit = min(params.get("limit", 100), 100)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{thread_id}/thread-members",
            headers=get_headers(),
            params={"limit": limit, "with_member": "true"},
        )
        resp.raise_for_status()
        members = resp.json()
        formatted = [
            {
                "user_id": m.get("user_id"),
                "join_timestamp": m.get("join_timestamp"),
            }
            for m in members
        ]
        return json.dumps(formatted, indent=2)


async def handle_threads_list_archived_public(params: dict) -> str:
    channel_id = params["channel_id"]
    limit = params.get("limit", 50)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/threads/archived/public",
            headers=get_headers(),
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        threads = [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "archived": t.get("thread_metadata", {}).get("archived"),
                "archive_timestamp": t.get("thread_metadata", {}).get("archive_timestamp"),
            }
            for t in data.get("threads", [])
        ]
        return json.dumps({"threads": threads, "has_more": data.get("has_more", False)}, indent=2)


async def handle_threads_list_archived_private(params: dict) -> str:
    channel_id = params["channel_id"]
    limit = params.get("limit", 50)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/threads/archived/private",
            headers=get_headers(),
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        threads = [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "archived": t.get("thread_metadata", {}).get("archived"),
                "archive_timestamp": t.get("thread_metadata", {}).get("archive_timestamp"),
            }
            for t in data.get("threads", [])
        ]
        return json.dumps({"threads": threads, "has_more": data.get("has_more", False)}, indent=2)


# ============================================================================
# CHANNEL HANDLERS
# ============================================================================


async def handle_channels_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/channels",
            headers=get_headers(),
        )
        resp.raise_for_status()
        channels = resp.json()
        formatted = [format_channel(c) for c in channels]
        return json.dumps(formatted, indent=2)


async def handle_channels_get(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_channel(resp.json()), indent=2)


async def handle_channels_create(params: dict) -> str:
    payload = {"name": params["name"]}

    if params.get("type") is not None:
        payload["type"] = params["type"]
    if params.get("topic"):
        payload["topic"] = params["topic"]
    if params.get("parent_id"):
        payload["parent_id"] = params["parent_id"]
    if params.get("nsfw") is not None:
        payload["nsfw"] = params["nsfw"]
    if params.get("slowmode") is not None:
        payload["rate_limit_per_user"] = params["slowmode"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/channels",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        channel = resp.json()
        return f"Channel created: {channel['name']} (ID: {channel['id']})"


async def handle_channels_edit(params: dict) -> str:
    channel_id = params["channel_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("topic") is not None:
        payload["topic"] = params["topic"]
    if params.get("nsfw") is not None:
        payload["nsfw"] = params["nsfw"]
    if params.get("slowmode") is not None:
        payload["rate_limit_per_user"] = params["slowmode"]
    if params.get("parent_id"):
        payload["parent_id"] = params["parent_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Channel {channel_id} edited"


async def handle_channels_delete(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Channel {channel_id} deleted"


async def handle_channels_set_permissions(params: dict) -> str:
    channel_id = params["channel_id"]
    target_id = params["target_id"]
    target_type = 0 if params["target_type"] == "role" else 1

    payload = {"type": target_type}
    if params.get("allow"):
        payload["allow"] = params["allow"]
    if params.get("deny"):
        payload["deny"] = params["deny"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/channels/{channel_id}/permissions/{target_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Permissions set for {target_id} on channel {channel_id}"


async def handle_channels_delete_permissions(params: dict) -> str:
    channel_id = params["channel_id"]
    target_id = params["target_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/channels/{channel_id}/permissions/{target_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Permissions deleted for {target_id} on channel {channel_id}"


# ============================================================================
# MEMBER HANDLERS
# ============================================================================


async def handle_members_list(params: dict) -> str:
    limit = min(params.get("limit", 100), 1000)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/members",
            headers=get_headers(),
            params={"limit": limit},
        )
        resp.raise_for_status()
        members = resp.json()
        formatted = [format_member(m) for m in members]
        return json.dumps(formatted, indent=2)


async def handle_members_get(params: dict) -> str:
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_member(resp.json()), indent=2)


async def handle_members_search(params: dict) -> str:
    query = params["query"]
    limit = min(params.get("limit", 100), 1000)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/search",
            headers=get_headers(),
            params={"query": query, "limit": limit},
        )
        resp.raise_for_status()
        members = resp.json()
        formatted = [format_member(m) for m in members]
        return json.dumps(formatted, indent=2)


async def handle_members_edit(params: dict) -> str:
    user_id = params["user_id"]
    payload = {}

    if "nick" in params:
        payload["nick"] = params["nick"] or None
    if params.get("mute") is not None:
        payload["mute"] = params["mute"]
    if params.get("deaf") is not None:
        payload["deaf"] = params["deaf"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Member {user_id} edited"


async def handle_members_add_role(params: dict) -> str:
    user_id = params["user_id"]
    role_id = params["role_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Role {role_id} added to user {user_id}"


async def handle_members_remove_role(params: dict) -> str:
    user_id = params["user_id"]
    role_id = params["role_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Role {role_id} removed from user {user_id}"


# ============================================================================
# MODERATION HANDLERS
# ============================================================================


async def handle_moderation_kick(params: dict) -> str:
    user_id = params["user_id"]
    reason = params.get("reason")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(reason),
        )
        resp.raise_for_status()
        return f"User {user_id} kicked"


async def handle_moderation_ban(params: dict) -> str:
    user_id = params["user_id"]
    reason = params.get("reason")
    delete_days = params.get("delete_message_days", 0)

    payload = {}
    if delete_days:
        payload["delete_message_seconds"] = delete_days * 86400

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/guilds/{GUILD_ID}/bans/{user_id}",
            headers=get_headers(reason),
            json=payload if payload else None,
        )
        resp.raise_for_status()
        return f"User {user_id} banned"


async def handle_moderation_unban(params: dict) -> str:
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/bans/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"User {user_id} unbanned"


async def handle_moderation_list_bans(params: dict) -> str:
    limit = params.get("limit", 100)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/bans",
            headers=get_headers(),
            params={"limit": limit},
        )
        resp.raise_for_status()
        bans = resp.json()
        formatted = [{"user": format_user(b["user"]), "reason": b.get("reason")} for b in bans]
        return json.dumps(formatted, indent=2)


async def handle_moderation_get_ban(params: dict) -> str:
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/bans/{user_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        ban = resp.json()
        return json.dumps({"user": format_user(ban["user"]), "reason": ban.get("reason")}, indent=2)


async def handle_moderation_timeout(params: dict) -> str:
    user_id = params["user_id"]
    duration_seconds = params["duration_seconds"]
    reason = params.get("reason")

    timeout_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(reason),
            json={"communication_disabled_until": timeout_until.isoformat()},
        )
        resp.raise_for_status()
        return f"User {user_id} timed out for {duration_seconds} seconds"


async def handle_moderation_remove_timeout(params: dict) -> str:
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(),
            json={"communication_disabled_until": None},
        )
        resp.raise_for_status()
        return f"Timeout removed from user {user_id}"


# ============================================================================
# ROLE HANDLERS
# ============================================================================


async def handle_roles_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles",
            headers=get_headers(),
        )
        resp.raise_for_status()
        roles = resp.json()
        formatted = [format_role(r) for r in roles]
        return json.dumps(formatted, indent=2)


async def handle_roles_get(params: dict) -> str:
    role_id = params["role_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles",
            headers=get_headers(),
        )
        resp.raise_for_status()
        roles = resp.json()
        role = next((r for r in roles if r["id"] == role_id), None)
        if not role:
            return f"Role {role_id} not found"
        return json.dumps(format_role(role), indent=2)


async def handle_roles_create(params: dict) -> str:
    payload = {"name": params["name"]}

    if params.get("color") is not None:
        payload["color"] = params["color"]
    if params.get("hoist") is not None:
        payload["hoist"] = params["hoist"]
    if params.get("mentionable") is not None:
        payload["mentionable"] = params["mentionable"]
    if params.get("permissions"):
        payload["permissions"] = params["permissions"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        role = resp.json()
        return f"Role created: {role['name']} (ID: {role['id']})"


async def handle_roles_edit(params: dict) -> str:
    role_id = params["role_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("color") is not None:
        payload["color"] = params["color"]
    if params.get("hoist") is not None:
        payload["hoist"] = params["hoist"]
    if params.get("mentionable") is not None:
        payload["mentionable"] = params["mentionable"]
    if params.get("permissions"):
        payload["permissions"] = params["permissions"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles/{role_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Role {role_id} edited"


async def handle_roles_delete(params: dict) -> str:
    role_id = params["role_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles/{role_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Role {role_id} deleted"


async def handle_roles_reorder(params: dict) -> str:
    roles = params["roles"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/roles",
            headers=get_headers(),
            json=roles,
        )
        resp.raise_for_status()
        return f"Reordered {len(roles)} roles"


# ============================================================================
# INVITE HANDLERS
# ============================================================================


async def handle_invites_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/invites",
            headers=get_headers(),
        )
        resp.raise_for_status()
        invites = resp.json()
        formatted = [format_invite(i) for i in invites]
        return json.dumps(formatted, indent=2)


async def handle_invites_create(params: dict) -> str:
    channel_id = params["channel_id"]
    payload = {}

    if params.get("max_age") is not None:
        payload["max_age"] = params["max_age"]
    if params.get("max_uses") is not None:
        payload["max_uses"] = params["max_uses"]
    if params.get("unique") is not None:
        payload["unique"] = params["unique"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/invites",
            headers=get_headers(),
            json=payload if payload else {},
        )
        resp.raise_for_status()
        invite = resp.json()
        return f"Invite created: https://discord.gg/{invite['code']}"


async def handle_invites_get(params: dict) -> str:
    invite_code = params["invite_code"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/invites/{invite_code}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_invite(resp.json()), indent=2)


async def handle_invites_delete(params: dict) -> str:
    invite_code = params["invite_code"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/invites/{invite_code}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Invite {invite_code} revoked"


# ============================================================================
# EVENT HANDLERS
# ============================================================================


async def handle_events_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events",
            headers=get_headers(),
        )
        resp.raise_for_status()
        events = resp.json()
        formatted = [format_event(e) for e in events]
        return json.dumps(formatted, indent=2)


async def handle_events_get(params: dict) -> str:
    event_id = params["event_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{event_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_event(resp.json()), indent=2)


async def handle_events_create(params: dict) -> str:
    name = params["name"]
    start_time = params["start_time"]

    payload = {
        "name": name,
        "scheduled_start_time": start_time,
        "privacy_level": 2,
    }

    if params.get("description"):
        payload["description"] = params["description"]
    if params.get("end_time"):
        payload["scheduled_end_time"] = params["end_time"]

    if params.get("channel_id"):
        payload["channel_id"] = params["channel_id"]
        payload["entity_type"] = 2
    else:
        payload["entity_type"] = 3
        payload["entity_metadata"] = {"location": params.get("location", "Online")}
        if not params.get("end_time"):
            payload["scheduled_end_time"] = start_time

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        event = resp.json()
        return f"Event created: {event['name']} (ID: {event['id']})"


async def handle_events_edit(params: dict) -> str:
    event_id = params["event_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("description") is not None:
        payload["description"] = params["description"]
    if params.get("start_time"):
        payload["scheduled_start_time"] = params["start_time"]
    if params.get("end_time"):
        payload["scheduled_end_time"] = params["end_time"]
    if params.get("status") is not None:
        payload["status"] = params["status"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{event_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Event {event_id} edited"


async def handle_events_delete(params: dict) -> str:
    event_id = params["event_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{event_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Event {event_id} deleted"


async def handle_events_list_users(params: dict) -> str:
    event_id = params["event_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{event_id}/users",
            headers=get_headers(),
        )
        resp.raise_for_status()
        users = resp.json()
        formatted = [format_user(u.get("user", {})) for u in users]
        return json.dumps(formatted, indent=2)


# ============================================================================
# POLL HANDLERS
# ============================================================================


async def handle_polls_create(params: dict) -> str:
    channel_id = params["channel_id"]
    question = params["question"]
    answers = params["answers"]
    duration = params.get("duration_hours", 24)
    multiselect = params.get("allow_multiselect", False)

    poll_answers = [{"poll_media": {"text": ans}} for ans in answers]

    payload = {
        "poll": {
            "question": {"text": question},
            "answers": poll_answers,
            "duration": duration,
            "allow_multiselect": multiselect,
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/messages",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        msg = resp.json()
        return f"Poll created (Message ID: {msg['id']})"


async def handle_polls_end(params: dict) -> str:
    channel_id = params["channel_id"]
    message_id = params["message_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/polls/{message_id}/expire",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Poll {message_id} ended"


# ============================================================================
# GUILD HANDLERS
# ============================================================================


async def handle_guild_get(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}",
            headers=get_headers(),
            params={"with_counts": "true"},
        )
        resp.raise_for_status()
        guild = resp.json()
        return json.dumps({
            "id": guild.get("id"),
            "name": guild.get("name"),
            "description": guild.get("description"),
            "member_count": guild.get("approximate_member_count"),
            "online_count": guild.get("approximate_presence_count"),
            "owner_id": guild.get("owner_id"),
            "verification_level": guild.get("verification_level"),
        }, indent=2)


async def handle_guild_edit(params: dict) -> str:
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("description") is not None:
        payload["description"] = params["description"]
    if params.get("verification_level") is not None:
        payload["verification_level"] = params["verification_level"]
    if params.get("default_message_notifications") is not None:
        payload["default_message_notifications"] = params["default_message_notifications"]
    if params.get("explicit_content_filter") is not None:
        payload["explicit_content_filter"] = params["explicit_content_filter"]
    if params.get("afk_channel_id"):
        payload["afk_channel_id"] = params["afk_channel_id"]
    if params.get("afk_timeout") is not None:
        payload["afk_timeout"] = params["afk_timeout"]
    if params.get("system_channel_id"):
        payload["system_channel_id"] = params["system_channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return "Server settings updated"


async def handle_guild_get_prune_count(params: dict) -> str:
    days = params["days"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/prune",
            headers=get_headers(),
            params={"days": days},
        )
        resp.raise_for_status()
        data = resp.json()
        return f"{data['pruned']} members would be pruned"


async def handle_guild_prune(params: dict) -> str:
    days = params["days"]
    compute_count = params.get("compute_prune_count", True)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/prune",
            headers=get_headers(),
            json={"days": days, "compute_prune_count": compute_count},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("pruned") is not None:
            return f"Pruned {data['pruned']} members"
        return "Prune initiated"


# ============================================================================
# AUDIT LOG HANDLERS
# ============================================================================


async def handle_audit_log_list(params: dict) -> str:
    query_params = {}

    if params.get("user_id"):
        query_params["user_id"] = params["user_id"]
    if params.get("action_type") is not None:
        query_params["action_type"] = params["action_type"]
    query_params["limit"] = params.get("limit", 50)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/audit-logs",
            headers=get_headers(),
            params=query_params,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = [format_audit_entry(e) for e in data.get("audit_log_entries", [])]
        return json.dumps(entries, indent=2)


# ============================================================================
# AUTOMOD HANDLERS
# ============================================================================


async def handle_automod_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules",
            headers=get_headers(),
        )
        resp.raise_for_status()
        rules = resp.json()
        formatted = [format_automod_rule(r) for r in rules]
        return json.dumps(formatted, indent=2)


async def handle_automod_get(params: dict) -> str:
    rule_id = params["rule_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{rule_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_automod_rule(resp.json()), indent=2)


async def handle_automod_create(params: dict) -> str:
    payload = {
        "name": params["name"],
        "event_type": params["event_type"],
        "trigger_type": params["trigger_type"],
        "actions": params["actions"],
    }

    if params.get("trigger_metadata"):
        payload["trigger_metadata"] = params["trigger_metadata"]
    if params.get("enabled") is not None:
        payload["enabled"] = params["enabled"]
    if params.get("exempt_roles"):
        payload["exempt_roles"] = params["exempt_roles"]
    if params.get("exempt_channels"):
        payload["exempt_channels"] = params["exempt_channels"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        rule = resp.json()
        return f"Automod rule created: {rule['name']} (ID: {rule['id']})"


async def handle_automod_edit(params: dict) -> str:
    rule_id = params["rule_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("trigger_metadata"):
        payload["trigger_metadata"] = params["trigger_metadata"]
    if params.get("actions"):
        payload["actions"] = params["actions"]
    if params.get("enabled") is not None:
        payload["enabled"] = params["enabled"]
    if params.get("exempt_roles"):
        payload["exempt_roles"] = params["exempt_roles"]
    if params.get("exempt_channels"):
        payload["exempt_channels"] = params["exempt_channels"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{rule_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Automod rule {rule_id} edited"


async def handle_automod_delete(params: dict) -> str:
    rule_id = params["rule_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{rule_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Automod rule {rule_id} deleted"


# ============================================================================
# WEBHOOK HANDLERS
# ============================================================================


async def handle_webhooks_list_guild(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/webhooks",
            headers=get_headers(),
        )
        resp.raise_for_status()
        webhooks = resp.json()
        formatted = [format_webhook(w) for w in webhooks]
        return json.dumps(formatted, indent=2)


async def handle_webhooks_list_channel(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}/webhooks",
            headers=get_headers(),
        )
        resp.raise_for_status()
        webhooks = resp.json()
        formatted = [format_webhook(w) for w in webhooks]
        return json.dumps(formatted, indent=2)


async def handle_webhooks_create(params: dict) -> str:
    channel_id = params["channel_id"]
    name = params["name"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/webhooks",
            headers=get_headers(),
            json={"name": name},
        )
        resp.raise_for_status()
        webhook = resp.json()
        return f"Webhook created: {webhook['name']} (URL: {webhook['url']})"


async def handle_webhooks_get(params: dict) -> str:
    webhook_id = params["webhook_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/webhooks/{webhook_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(format_webhook(resp.json()), indent=2)


async def handle_webhooks_edit(params: dict) -> str:
    webhook_id = params["webhook_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("channel_id"):
        payload["channel_id"] = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/webhooks/{webhook_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Webhook {webhook_id} edited"


async def handle_webhooks_delete(params: dict) -> str:
    webhook_id = params["webhook_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/webhooks/{webhook_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Webhook {webhook_id} deleted"


async def handle_webhooks_send(params: dict) -> str:
    webhook_url = params["webhook_url"]

    payload = {}
    if params.get("content"):
        payload["content"] = params["content"]
    if params.get("username"):
        payload["username"] = params["username"]
    if params.get("avatar_url"):
        payload["avatar_url"] = params["avatar_url"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
        return "Webhook message sent"


# ============================================================================
# VOICE HANDLERS
# ============================================================================


async def handle_voice_move_member(params: dict) -> str:
    user_id = params["user_id"]
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(),
            json={"channel_id": channel_id},
        )
        resp.raise_for_status()
        return f"User {user_id} moved to voice channel {channel_id}"


async def handle_voice_disconnect_member(params: dict) -> str:
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/members/{user_id}",
            headers=get_headers(),
            json={"channel_id": None},
        )
        resp.raise_for_status()
        return f"User {user_id} disconnected from voice"


# ============================================================================
# EMOJI HANDLERS
# ============================================================================


async def handle_emojis_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/emojis",
            headers=get_headers(),
        )
        resp.raise_for_status()
        emojis = resp.json()
        formatted = [{"id": e["id"], "name": e["name"], "animated": e.get("animated", False)} for e in emojis]
        return json.dumps(formatted, indent=2)


async def handle_emojis_get(params: dict) -> str:
    emoji_id = params["emoji_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{emoji_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        e = resp.json()
        return json.dumps({"id": e["id"], "name": e["name"], "animated": e.get("animated", False)}, indent=2)


async def handle_emojis_create(params: dict) -> str:
    name = params["name"]
    image_url = params["image_url"]

    async with httpx.AsyncClient() as client:
        # Download image
        img_resp = await client.get(image_url)
        img_resp.raise_for_status()

        content_type = img_resp.headers.get("content-type", "image/png")
        image_data = base64.b64encode(img_resp.content).decode("utf-8")
        data_uri = f"data:{content_type};base64,{image_data}"

        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/emojis",
            headers=get_headers(),
            json={"name": name, "image": data_uri},
        )
        resp.raise_for_status()
        emoji = resp.json()
        return f"Emoji created: {emoji['name']} (ID: {emoji['id']})"


async def handle_emojis_edit(params: dict) -> str:
    emoji_id = params["emoji_id"]
    name = params["name"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{emoji_id}",
            headers=get_headers(),
            json={"name": name},
        )
        resp.raise_for_status()
        return f"Emoji {emoji_id} renamed to {name}"


async def handle_emojis_delete(params: dict) -> str:
    emoji_id = params["emoji_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{emoji_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Emoji {emoji_id} deleted"


# ============================================================================
# STICKER HANDLERS
# ============================================================================


async def handle_stickers_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/stickers",
            headers=get_headers(),
        )
        resp.raise_for_status()
        stickers = resp.json()
        formatted = [{"id": s["id"], "name": s["name"], "description": s.get("description")} for s in stickers]
        return json.dumps(formatted, indent=2)


async def handle_stickers_get(params: dict) -> str:
    sticker_id = params["sticker_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/stickers/{sticker_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        s = resp.json()
        return json.dumps({"id": s["id"], "name": s["name"], "description": s.get("description")}, indent=2)


async def handle_stickers_delete(params: dict) -> str:
    sticker_id = params["sticker_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/stickers/{sticker_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Sticker {sticker_id} deleted"


# ============================================================================
# FORUM HANDLERS
# ============================================================================


async def handle_forum_create_post(params: dict) -> str:
    channel_id = params["channel_id"]
    name = params["name"]
    content = params["content"]

    payload = {
        "name": name,
        "message": {"content": content},
    }
    if params.get("applied_tags"):
        payload["applied_tags"] = params["applied_tags"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel_id}/threads",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        thread = resp.json()
        return f"Forum post created: {thread['name']} (ID: {thread['id']})"


async def handle_forum_list_tags(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        channel = resp.json()
        tags = channel.get("available_tags", [])
        formatted = [{"id": t["id"], "name": t["name"], "moderated": t.get("moderated", False)} for t in tags]
        return json.dumps(formatted, indent=2)


async def handle_forum_create_tag(params: dict) -> str:
    channel_id = params["channel_id"]

    # Get current tags first
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/channels/{channel_id}", headers=get_headers())
        resp.raise_for_status()
        channel = resp.json()
        current_tags = channel.get("available_tags", [])

        new_tag = {"name": params["name"]}
        if params.get("moderated") is not None:
            new_tag["moderated"] = params["moderated"]
        if params.get("emoji_name"):
            new_tag["emoji_name"] = params["emoji_name"]

        current_tags.append(new_tag)

        resp = await client.patch(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
            json={"available_tags": current_tags},
        )
        resp.raise_for_status()
        return f"Tag '{params['name']}' created"


async def handle_forum_edit_tag(params: dict) -> str:
    channel_id = params["channel_id"]
    tag_id = params["tag_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/channels/{channel_id}", headers=get_headers())
        resp.raise_for_status()
        channel = resp.json()
        tags = channel.get("available_tags", [])

        for tag in tags:
            if tag["id"] == tag_id:
                if params.get("name"):
                    tag["name"] = params["name"]
                if params.get("moderated") is not None:
                    tag["moderated"] = params["moderated"]
                break

        resp = await client.patch(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
            json={"available_tags": tags},
        )
        resp.raise_for_status()
        return f"Tag {tag_id} edited"


async def handle_forum_delete_tag(params: dict) -> str:
    channel_id = params["channel_id"]
    tag_id = params["tag_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/channels/{channel_id}", headers=get_headers())
        resp.raise_for_status()
        channel = resp.json()
        tags = [t for t in channel.get("available_tags", []) if t["id"] != tag_id]

        resp = await client.patch(
            f"{BASE_URL}/channels/{channel_id}",
            headers=get_headers(),
            json={"available_tags": tags},
        )
        resp.raise_for_status()
        return f"Tag {tag_id} deleted"


# ============================================================================
# STAGE HANDLERS
# ============================================================================


async def handle_stage_create_instance(params: dict) -> str:
    channel_id = params["channel_id"]
    topic = params["topic"]

    payload = {
        "channel_id": channel_id,
        "topic": topic,
        "privacy_level": params.get("privacy_level", 2),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/stage-instances",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Stage instance started: {topic}"


async def handle_stage_get_instance(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/stage-instances/{channel_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        instance = resp.json()
        return json.dumps({
            "channel_id": instance.get("channel_id"),
            "topic": instance.get("topic"),
            "privacy_level": instance.get("privacy_level"),
        }, indent=2)


async def handle_stage_edit_instance(params: dict) -> str:
    channel_id = params["channel_id"]
    topic = params["topic"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/stage-instances/{channel_id}",
            headers=get_headers(),
            json={"topic": topic},
        )
        resp.raise_for_status()
        return f"Stage topic updated to: {topic}"


async def handle_stage_delete_instance(params: dict) -> str:
    channel_id = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/stage-instances/{channel_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return "Stage instance ended"


async def handle_stage_invite_speaker(params: dict) -> str:
    channel_id = params["channel_id"]
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/voice-states/{user_id}",
            headers=get_headers(),
            json={"channel_id": channel_id, "suppress": False},
        )
        resp.raise_for_status()
        return f"User {user_id} invited to speak"


async def handle_stage_move_to_audience(params: dict) -> str:
    channel_id = params["channel_id"]
    user_id = params["user_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/voice-states/{user_id}",
            headers=get_headers(),
            json={"channel_id": channel_id, "suppress": True},
        )
        resp.raise_for_status()
        return f"User {user_id} moved to audience"


# ============================================================================
# ONBOARDING HANDLERS
# ============================================================================


async def handle_onboarding_get(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/onboarding",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)


async def handle_onboarding_edit(params: dict) -> str:
    payload = {}
    if params.get("prompts"):
        payload["prompts"] = params["prompts"]
    if params.get("default_channel_ids"):
        payload["default_channel_ids"] = params["default_channel_ids"]
    if params.get("enabled") is not None:
        payload["enabled"] = params["enabled"]
    if params.get("mode") is not None:
        payload["mode"] = params["mode"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/guilds/{GUILD_ID}/onboarding",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return "Onboarding settings updated"


async def handle_onboarding_create_prompt(params: dict) -> str:
    payload = {
        "title": params["title"],
        "options": params["options"],
    }
    if params.get("single_select") is not None:
        payload["single_select"] = params["single_select"]
    if params.get("required") is not None:
        payload["required"] = params["required"]
    if params.get("in_onboarding") is not None:
        payload["in_onboarding"] = params["in_onboarding"]
    if params.get("type") is not None:
        payload["type"] = params["type"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/onboarding/prompts",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return f"Onboarding prompt created: {data.get('title')} (ID: {data.get('id')})"


# ============================================================================
# WELCOME SCREEN HANDLERS
# ============================================================================


async def handle_welcome_screen_get(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/welcome-screen",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)


async def handle_welcome_screen_edit(params: dict) -> str:
    payload = {}
    if params.get("enabled") is not None:
        payload["enabled"] = params["enabled"]
    if params.get("description") is not None:
        payload["description"] = params["description"]
    if params.get("welcome_channels"):
        payload["welcome_channels"] = params["welcome_channels"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/welcome-screen",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return "Welcome screen updated"


# ============================================================================
# SOUNDBOARD HANDLERS
# ============================================================================


async def handle_soundboard_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds",
            headers=get_headers(),
        )
        resp.raise_for_status()
        sounds = resp.json().get("items", [])
        formatted = [{"id": s["sound_id"], "name": s["name"], "volume": s.get("volume", 1)} for s in sounds]
        return json.dumps(formatted, indent=2)


async def handle_soundboard_get(params: dict) -> str:
    sound_id = params["sound_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{sound_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        s = resp.json()
        return json.dumps({"id": s["sound_id"], "name": s["name"], "volume": s.get("volume", 1)}, indent=2)


async def handle_soundboard_create(params: dict) -> str:
    name = params["name"]
    sound_url = params["sound_url"]

    async with httpx.AsyncClient() as client:
        # Download sound file
        snd_resp = await client.get(sound_url)
        snd_resp.raise_for_status()

        content_type = snd_resp.headers.get("content-type", "audio/mpeg")
        sound_data = base64.b64encode(snd_resp.content).decode("utf-8")
        data_uri = f"data:{content_type};base64,{sound_data}"

        payload = {"name": name, "sound": data_uri}
        if params.get("volume") is not None:
            payload["volume"] = params["volume"]
        if params.get("emoji_name"):
            payload["emoji_name"] = params["emoji_name"]

        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        sound = resp.json()
        return f"Sound created: {sound['name']} (ID: {sound['sound_id']})"


async def handle_soundboard_edit(params: dict) -> str:
    sound_id = params["sound_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("volume") is not None:
        payload["volume"] = params["volume"]
    if params.get("emoji_name"):
        payload["emoji_name"] = params["emoji_name"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{sound_id}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Sound {sound_id} edited"


async def handle_soundboard_delete(params: dict) -> str:
    sound_id = params["sound_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{sound_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Sound {sound_id} deleted"


# ============================================================================
# APPLICATION COMMANDS HANDLERS
# ============================================================================


async def handle_commands_list_global(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        # Get application ID first
        resp = await client.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers())
        resp.raise_for_status()
        app_id = resp.json()["id"]

        resp = await client.get(
            f"{BASE_URL}/applications/{app_id}/commands",
            headers=get_headers(),
        )
        resp.raise_for_status()
        commands = resp.json()
        formatted = [{"id": c["id"], "name": c["name"], "description": c.get("description")} for c in commands]
        return json.dumps(formatted, indent=2)


async def handle_commands_list_guild(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers())
        resp.raise_for_status()
        app_id = resp.json()["id"]

        resp = await client.get(
            f"{BASE_URL}/applications/{app_id}/guilds/{GUILD_ID}/commands",
            headers=get_headers(),
        )
        resp.raise_for_status()
        commands = resp.json()
        formatted = [{"id": c["id"], "name": c["name"], "description": c.get("description")} for c in commands]
        return json.dumps(formatted, indent=2)


async def handle_commands_create(params: dict) -> str:
    name = params["name"]
    description = params["description"]
    guild_only = params.get("guild_only", True)

    payload = {"name": name, "description": description, "type": 1}
    if params.get("options"):
        payload["options"] = params["options"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers())
        resp.raise_for_status()
        app_id = resp.json()["id"]

        if guild_only:
            url = f"{BASE_URL}/applications/{app_id}/guilds/{GUILD_ID}/commands"
        else:
            url = f"{BASE_URL}/applications/{app_id}/commands"

        resp = await client.post(url, headers=get_headers(), json=payload)
        resp.raise_for_status()
        cmd = resp.json()
        return f"Command created: /{cmd['name']} (ID: {cmd['id']})"


async def handle_commands_edit(params: dict) -> str:
    command_id = params["command_id"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("description"):
        payload["description"] = params["description"]
    if params.get("options"):
        payload["options"] = params["options"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers())
        resp.raise_for_status()
        app_id = resp.json()["id"]

        # Try guild first, then global
        resp = await client.patch(
            f"{BASE_URL}/applications/{app_id}/guilds/{GUILD_ID}/commands/{command_id}",
            headers=get_headers(),
            json=payload,
        )
        if resp.status_code == 404:
            resp = await client.patch(
                f"{BASE_URL}/applications/{app_id}/commands/{command_id}",
                headers=get_headers(),
                json=payload,
            )
        resp.raise_for_status()
        return f"Command {command_id} edited"


async def handle_commands_delete(params: dict) -> str:
    command_id = params["command_id"]
    guild_only = params.get("guild_only", True)

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers())
        resp.raise_for_status()
        app_id = resp.json()["id"]

        if guild_only:
            url = f"{BASE_URL}/applications/{app_id}/guilds/{GUILD_ID}/commands/{command_id}"
        else:
            url = f"{BASE_URL}/applications/{app_id}/commands/{command_id}"

        resp = await client.delete(url, headers=get_headers())
        resp.raise_for_status()
        return f"Command {command_id} deleted"


# ============================================================================
# INTEGRATIONS HANDLERS
# ============================================================================


async def handle_integrations_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/integrations",
            headers=get_headers(),
        )
        resp.raise_for_status()
        integrations = resp.json()
        formatted = [{"id": i["id"], "name": i["name"], "type": i["type"]} for i in integrations]
        return json.dumps(formatted, indent=2)


async def handle_integrations_delete(params: dict) -> str:
    integration_id = params["integration_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/integrations/{integration_id}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Integration {integration_id} deleted"


# ============================================================================
# WIDGET HANDLERS
# ============================================================================


async def handle_widget_get(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/widget",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)


async def handle_widget_get_data(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/widget.json",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)


async def handle_widget_edit(params: dict) -> str:
    payload = {}
    if params.get("enabled") is not None:
        payload["enabled"] = params["enabled"]
    if params.get("channel_id"):
        payload["channel_id"] = params["channel_id"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/widget",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return "Widget settings updated"


# ============================================================================
# VANITY URL HANDLERS
# ============================================================================


async def handle_vanity_get(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/vanity-url",
            headers=get_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return json.dumps({"code": data.get("code"), "uses": data.get("uses")}, indent=2)


async def handle_vanity_edit(params: dict) -> str:
    code = params["code"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/vanity-url",
            headers=get_headers(),
            json={"code": code},
        )
        resp.raise_for_status()
        return f"Vanity URL set to: discord.gg/{code}"


# ============================================================================
# TEMPLATE HANDLERS
# ============================================================================


async def handle_templates_list(params: dict) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/{GUILD_ID}/templates",
            headers=get_headers(),
        )
        resp.raise_for_status()
        templates = resp.json()
        formatted = [{"code": t["code"], "name": t["name"], "description": t.get("description")} for t in templates]
        return json.dumps(formatted, indent=2)


async def handle_templates_get(params: dict) -> str:
    template_code = params["template_code"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/guilds/templates/{template_code}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        t = resp.json()
        return json.dumps({"code": t["code"], "name": t["name"], "description": t.get("description")}, indent=2)


async def handle_templates_create(params: dict) -> str:
    name = params["name"]

    payload = {"name": name}
    if params.get("description"):
        payload["description"] = params["description"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/templates",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        t = resp.json()
        return f"Template created: {t['name']} (code: {t['code']})"


async def handle_templates_sync(params: dict) -> str:
    template_code = params["template_code"]

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{BASE_URL}/guilds/{GUILD_ID}/templates/{template_code}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Template {template_code} synced with current server state"


async def handle_templates_edit(params: dict) -> str:
    template_code = params["template_code"]
    payload = {}

    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("description") is not None:
        payload["description"] = params["description"]

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{BASE_URL}/guilds/{GUILD_ID}/templates/{template_code}",
            headers=get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Template {template_code} edited"


async def handle_templates_delete(params: dict) -> str:
    template_code = params["template_code"]

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{BASE_URL}/guilds/{GUILD_ID}/templates/{template_code}",
            headers=get_headers(),
        )
        resp.raise_for_status()
        return f"Template {template_code} deleted"


# ============================================================================
# DM HANDLERS
# ============================================================================


async def handle_dm_send(params: dict) -> str:
    user_id = params["user_id"]
    content = params["content"]

    async with httpx.AsyncClient() as client:
        # Create DM channel first
        resp = await client.post(
            f"{BASE_URL}/users/@me/channels",
            headers=get_headers(),
            json={"recipient_id": user_id},
        )
        resp.raise_for_status()
        dm_channel = resp.json()

        # Send message
        resp = await client.post(
            f"{BASE_URL}/channels/{dm_channel['id']}/messages",
            headers=get_headers(),
            json={"content": content},
        )
        resp.raise_for_status()
        return f"DM sent to user {user_id}"


# ============================================================================
# BULK BAN HANDLERS
# ============================================================================


async def handle_bulk_ban_execute(params: dict) -> str:
    user_ids = params["user_ids"]

    payload = {"user_ids": user_ids}
    if params.get("delete_message_seconds"):
        payload["delete_message_seconds"] = params["delete_message_seconds"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/guilds/{GUILD_ID}/bulk-ban",
            headers=get_headers(params.get("reason")),
            json=payload,
        )
        resp.raise_for_status()
        result = resp.json()
        banned = len(result.get("banned_users", []))
        failed = len(result.get("failed_users", []))
        return f"Bulk ban complete: {banned} banned, {failed} failed"


# ============================================================================
# BATCH HANDLERS
# ============================================================================

BATCH_CONCURRENCY = 10
BATCH_DELAY_MS = 50


async def handle_batch_members_add_role(params: dict) -> str:
    role_id = params["role_id"]
    member_ids = params["member_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def add_role_to_member(member_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.put(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}/roles/{role_id}",
                        headers=get_headers(),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"member_id": member_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"member_id": member_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[add_role_to_member(m) for m in member_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_members_remove_role(params: dict) -> str:
    role_id = params["role_id"]
    member_ids = params["member_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def remove_role_from_member(member_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}/roles/{role_id}",
                        headers=get_headers(),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"member_id": member_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"member_id": member_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[remove_role_from_member(m) for m in member_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_channels_set_permissions(params: dict) -> str:
    channel_ids = params["channel_ids"]
    target_id = params["target_id"]
    target_type = 0 if params["target_type"] == "role" else 1

    payload = {"type": target_type}
    if params.get("allow"):
        payload["allow"] = params["allow"]
    if params.get("deny"):
        payload["deny"] = params["deny"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def set_permissions_on_channel(channel_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.put(
                        f"{BASE_URL}/channels/{channel_id}/permissions/{target_id}",
                        headers=get_headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"channel_id": channel_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"channel_id": channel_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[set_permissions_on_channel(c) for c in channel_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_members_timeout(params: dict) -> str:
    member_ids = params["member_ids"]
    duration_seconds = params["duration_seconds"]
    reason = params.get("reason")
    timeout_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def timeout_member(member_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.patch(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}",
                        headers=get_headers(reason),
                        json={"communication_disabled_until": timeout_until.isoformat()},
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"member_id": member_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"member_id": member_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[timeout_member(m) for m in member_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_members_kick(params: dict) -> str:
    member_ids = params["member_ids"]
    reason = params.get("reason")

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def kick_member(member_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}",
                        headers=get_headers(reason),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"member_id": member_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"member_id": member_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[kick_member(m) for m in member_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_channels_delete(params: dict) -> str:
    channel_ids = params["channel_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def delete_channel(channel_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"{BASE_URL}/channels/{channel_id}",
                        headers=get_headers(),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"channel_id": channel_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"channel_id": channel_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[delete_channel(c) for c in channel_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_channels_edit(params: dict) -> str:
    channel_ids = params["channel_ids"]

    payload = {}
    if params.get("name"):
        payload["name"] = params["name"]
    if params.get("topic") is not None:
        payload["topic"] = params["topic"]
    if params.get("nsfw") is not None:
        payload["nsfw"] = params["nsfw"]
    if params.get("slowmode") is not None:
        payload["rate_limit_per_user"] = params["slowmode"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def edit_channel(channel_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.patch(
                        f"{BASE_URL}/channels/{channel_id}",
                        headers=get_headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"channel_id": channel_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"channel_id": channel_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[edit_channel(c) for c in channel_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_roles_add_to_member(params: dict) -> str:
    member_id = params["member_id"]
    role_ids = params["role_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def add_role(role_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.put(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}/roles/{role_id}",
                        headers=get_headers(),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"role_id": role_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"role_id": role_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[add_role(r) for r in role_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_roles_remove_from_member(params: dict) -> str:
    member_id = params["member_id"]
    role_ids = params["role_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def remove_role(role_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"{BASE_URL}/guilds/{GUILD_ID}/members/{member_id}/roles/{role_id}",
                        headers=get_headers(),
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"role_id": role_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"role_id": role_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[remove_role(r) for r in role_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


async def handle_batch_threads_archive(params: dict) -> str:
    thread_ids = params["thread_ids"]

    success = 0
    failed = 0
    errors = []
    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def archive_thread(thread_id: str) -> None:
        nonlocal success, failed
        async with semaphore:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.patch(
                        f"{BASE_URL}/channels/{thread_id}",
                        headers=get_headers(),
                        json={"archived": True},
                    )
                    resp.raise_for_status()
                    success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try:
                    detail = e.response.json().get("message", e.response.text)
                except Exception:
                    detail = e.response.text
                errors.append({"thread_id": thread_id, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1
                errors.append({"thread_id": thread_id, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)

    await asyncio.gather(*[archive_thread(t) for t in thread_ids])

    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)


# ============================================================================
# HANDLER REGISTRY
# ============================================================================

HANDLERS = {
    # Messages
    "messages.send": handle_messages_send,
    "messages.list": handle_messages_list,
    "messages.get": handle_messages_get,
    "messages.delete": handle_messages_delete,
    "messages.bulk_delete": handle_messages_bulk_delete,
    "messages.edit": handle_messages_edit,
    "messages.pin": handle_messages_pin,
    "messages.unpin": handle_messages_unpin,
    "messages.list_pins": handle_messages_list_pins,
    "messages.crosspost": handle_messages_crosspost,
    # Reactions
    "reactions.add": handle_reactions_add,
    "reactions.remove": handle_reactions_remove,
    "reactions.remove_user": handle_reactions_remove_user,
    "reactions.remove_all": handle_reactions_remove_all,
    "reactions.list": handle_reactions_list,
    # Threads
    "threads.create": handle_threads_create,
    "threads.list": handle_threads_list,
    "threads.join": handle_threads_join,
    "threads.leave": handle_threads_leave,
    "threads.add_member": handle_threads_add_member,
    "threads.remove_member": handle_threads_remove_member,
    "threads.archive": handle_threads_archive,
    "threads.unarchive": handle_threads_unarchive,
    "threads.lock": handle_threads_lock,
    "threads.delete": handle_threads_delete,
    "threads.list_members": handle_threads_list_members,
    "threads.list_archived_public": handle_threads_list_archived_public,
    "threads.list_archived_private": handle_threads_list_archived_private,
    # Channels
    "channels.list": handle_channels_list,
    "channels.get": handle_channels_get,
    "channels.create": handle_channels_create,
    "channels.edit": handle_channels_edit,
    "channels.delete": handle_channels_delete,
    "channels.set_permissions": handle_channels_set_permissions,
    "channels.delete_permissions": handle_channels_delete_permissions,
    # Members
    "members.list": handle_members_list,
    "members.get": handle_members_get,
    "members.search": handle_members_search,
    "members.edit": handle_members_edit,
    "members.add_role": handle_members_add_role,
    "members.remove_role": handle_members_remove_role,
    # Moderation
    "moderation.kick": handle_moderation_kick,
    "moderation.ban": handle_moderation_ban,
    "moderation.unban": handle_moderation_unban,
    "moderation.list_bans": handle_moderation_list_bans,
    "moderation.get_ban": handle_moderation_get_ban,
    "moderation.timeout": handle_moderation_timeout,
    "moderation.remove_timeout": handle_moderation_remove_timeout,
    # Roles
    "roles.list": handle_roles_list,
    "roles.get": handle_roles_get,
    "roles.create": handle_roles_create,
    "roles.edit": handle_roles_edit,
    "roles.delete": handle_roles_delete,
    "roles.reorder": handle_roles_reorder,
    # Invites
    "invites.list": handle_invites_list,
    "invites.create": handle_invites_create,
    "invites.get": handle_invites_get,
    "invites.delete": handle_invites_delete,
    # Events
    "events.list": handle_events_list,
    "events.get": handle_events_get,
    "events.create": handle_events_create,
    "events.edit": handle_events_edit,
    "events.delete": handle_events_delete,
    "events.list_users": handle_events_list_users,
    # Polls
    "polls.create": handle_polls_create,
    "polls.end": handle_polls_end,
    # Guild
    "guild.get": handle_guild_get,
    "guild.edit": handle_guild_edit,
    "guild.get_prune_count": handle_guild_get_prune_count,
    "guild.prune": handle_guild_prune,
    # Audit Log
    "audit_log.list": handle_audit_log_list,
    # Automod
    "automod.list": handle_automod_list,
    "automod.get": handle_automod_get,
    "automod.create": handle_automod_create,
    "automod.edit": handle_automod_edit,
    "automod.delete": handle_automod_delete,
    # Webhooks
    "webhooks.list_guild": handle_webhooks_list_guild,
    "webhooks.list_channel": handle_webhooks_list_channel,
    "webhooks.create": handle_webhooks_create,
    "webhooks.get": handle_webhooks_get,
    "webhooks.edit": handle_webhooks_edit,
    "webhooks.delete": handle_webhooks_delete,
    "webhooks.send": handle_webhooks_send,
    # Voice
    "voice.move_member": handle_voice_move_member,
    "voice.disconnect_member": handle_voice_disconnect_member,
    # Emojis
    "emojis.list": handle_emojis_list,
    "emojis.get": handle_emojis_get,
    "emojis.create": handle_emojis_create,
    "emojis.edit": handle_emojis_edit,
    "emojis.delete": handle_emojis_delete,
    # Stickers
    "stickers.list": handle_stickers_list,
    "stickers.get": handle_stickers_get,
    "stickers.delete": handle_stickers_delete,
    # Forum
    "forum.create_post": handle_forum_create_post,
    "forum.list_tags": handle_forum_list_tags,
    "forum.create_tag": handle_forum_create_tag,
    "forum.edit_tag": handle_forum_edit_tag,
    "forum.delete_tag": handle_forum_delete_tag,
    # Stage
    "stage.create_instance": handle_stage_create_instance,
    "stage.get_instance": handle_stage_get_instance,
    "stage.edit_instance": handle_stage_edit_instance,
    "stage.delete_instance": handle_stage_delete_instance,
    "stage.invite_speaker": handle_stage_invite_speaker,
    "stage.move_to_audience": handle_stage_move_to_audience,
    # Onboarding
    "onboarding.get": handle_onboarding_get,
    "onboarding.edit": handle_onboarding_edit,
    "onboarding.create_prompt": handle_onboarding_create_prompt,
    # Welcome Screen
    "welcome_screen.get": handle_welcome_screen_get,
    "welcome_screen.edit": handle_welcome_screen_edit,
    # Soundboard
    "soundboard.list": handle_soundboard_list,
    "soundboard.get": handle_soundboard_get,
    "soundboard.create": handle_soundboard_create,
    "soundboard.edit": handle_soundboard_edit,
    "soundboard.delete": handle_soundboard_delete,
    # Commands
    "commands.list_global": handle_commands_list_global,
    "commands.list_guild": handle_commands_list_guild,
    "commands.create": handle_commands_create,
    "commands.edit": handle_commands_edit,
    "commands.delete": handle_commands_delete,
    # Integrations
    "integrations.list": handle_integrations_list,
    "integrations.delete": handle_integrations_delete,
    # Widget
    "widget.get": handle_widget_get,
    "widget.get_data": handle_widget_get_data,
    "widget.edit": handle_widget_edit,
    # Vanity
    "vanity.get": handle_vanity_get,
    "vanity.edit": handle_vanity_edit,
    # Templates
    "templates.list": handle_templates_list,
    "templates.get": handle_templates_get,
    "templates.create": handle_templates_create,
    "templates.sync": handle_templates_sync,
    "templates.edit": handle_templates_edit,
    "templates.delete": handle_templates_delete,
    # DM
    "dm.send": handle_dm_send,
    # Bulk Ban
    "bulk_ban.execute": handle_bulk_ban_execute,
    # Batch
    "batch.members.add_role": handle_batch_members_add_role,
    "batch.members.remove_role": handle_batch_members_remove_role,
    "batch.channels.set_permissions": handle_batch_channels_set_permissions,
    "batch.members.timeout": handle_batch_members_timeout,
    "batch.members.kick": handle_batch_members_kick,
    "batch.channels.delete": handle_batch_channels_delete,
    "batch.channels.edit": handle_batch_channels_edit,
    "batch.roles.add_to_member": handle_batch_roles_add_to_member,
    "batch.roles.remove_from_member": handle_batch_roles_remove_from_member,
    "batch.threads.archive": handle_batch_threads_archive,
}


if __name__ == "__main__":
    mcp.run()
