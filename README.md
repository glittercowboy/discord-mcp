# Discord MCP Server

A Model Context Protocol (MCP) server that provides full administrative control over Discord communities. Enables AI assistants like Claude to manage Discord servers through 128 operations covering messages, moderation, channels, roles, events, and more.

## Features

- **Messages**: Send, read, edit, delete, pin messages and manage reactions
- **Moderation**: Kick, ban, timeout members with audit log support
- **Channels**: Create, edit, delete channels with permission management
- **Threads**: Create and manage threads and forum posts
- **Roles**: Full role CRUD with permission configuration
- **Members**: List, search, edit members and manage their roles
- **Events**: Create and manage scheduled events
- **Polls**: Create polls with multiple choice options
- **Webhooks**: Create and send messages via webhooks
- **AutoMod**: Configure auto-moderation rules
- **Voice**: Move and disconnect members from voice channels
- **And more**: Emojis, stickers, invites, templates, onboarding, stage channels...

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A Discord account
- A Discord server where you have admin permissions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/glittercowboy/discord-mcp.git
cd discord-mcp
```

2. Install dependencies:
```bash
uv sync
```

## Discord Bot Setup

Follow these steps carefully to create and configure your Discord bot.

### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Log in with your Discord account
3. Click the **"New Application"** button (top right)
4. Enter a name for your application (e.g., "My MCP Bot")
5. Accept the Terms of Service and click **"Create"**

### Step 2: Create the Bot User

1. In your application's settings, click **"Bot"** in the left sidebar
2. Click **"Add Bot"** and confirm by clicking **"Yes, do it!"**
3. Your bot is now created!

### Step 3: Get Your Bot Token

> **IMPORTANT**: Your bot token is like a password. Never share it or commit it to version control.

1. In the Bot section, find the **"Token"** area
2. Click **"Reset Token"** (or "Copy" if available)
3. You may need to enter your Discord password or 2FA code
4. **Copy the token immediately** - you can only see it once!
5. Store it somewhere safe (you'll need it for configuration)

If you lose your token, you'll need to reset it, which invalidates the old one.

### Step 4: Enable Privileged Intents

Still in the Bot section, scroll down to **"Privileged Gateway Intents"** and enable:

| Intent | Why It's Needed |
|--------|-----------------|
| **Server Members Intent** | Required for listing members, managing roles, and member-related operations |
| **Message Content Intent** | Required for reading message content (not just metadata) |

Click **"Save Changes"** at the bottom.

### Step 5: Generate the Bot Invite URL

1. Click **"OAuth2"** in the left sidebar
2. Click **"URL Generator"** under OAuth2

**Select these scopes:**
- `bot`
- `applications.commands`

**Select bot permissions:**

For full functionality, select **"Administrator"**.

Or for minimal permissions, select these individually:
- Manage Channels
- Manage Roles
- Kick Members
- Ban Members
- Manage Messages
- Read Message History
- Send Messages
- Create Public Threads
- Create Private Threads
- Manage Threads
- Embed Links
- Attach Files
- Add Reactions
- Use External Emojis
- Manage Webhooks
- View Audit Log
- Moderate Members (for timeouts)
- Manage Events
- Create Events
- Send Polls

3. Copy the generated URL at the bottom of the page

### Step 6: Invite the Bot to Your Server

1. Open the URL you copied in your browser
2. Select the server you want to add the bot to (you need "Manage Server" permission)
3. Review the permissions and click **"Authorize"**
4. Complete any CAPTCHA if prompted
5. The bot should now appear in your server's member list (it will show as offline until the MCP server runs)

### Step 7: Get Your Server (Guild) ID

1. Open Discord (desktop app or web)
2. Go to **User Settings** (gear icon near your username)
3. Navigate to **App Settings** > **Advanced**
4. Enable **"Developer Mode"**
5. Close settings
6. Right-click on your server name in the server list
7. Click **"Copy Server ID"**
8. Save this ID - you'll need it for configuration

## Configuration

You need two values:
- **Bot Token** (from Step 3)
- **Server ID** (from Step 7)

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "discord": {
      "command": "uv",
      "args": ["--directory", "/path/to/discord-mcp", "run", "python", "-m", "src.server"],
      "env": {
        "DISCORD_BOT_TOKEN": "your-bot-token-here",
        "DISCORD_GUILD_ID": "your-server-id-here"
      }
    }
  }
}
```

Replace:
- `/path/to/discord-mcp` with the actual path where you cloned the repo
- `your-bot-token-here` with your bot token from Step 3
- `your-server-id-here` with your server ID from Step 7

### Claude Code

Add to your MCP settings (`.claude/settings.json` or via `claude mcp add`):

```json
{
  "mcpServers": {
    "discord": {
      "command": "uv",
      "args": ["--directory", "/path/to/discord-mcp", "run", "python", "-m", "src.server"],
      "env": {
        "DISCORD_BOT_TOKEN": "your-bot-token-here",
        "DISCORD_GUILD_ID": "your-server-id-here"
      }
    }
  }
}
```

## Verifying Setup

After configuration, restart Claude Desktop/Code and try:

1. Ask Claude to discover available Discord operations
2. Ask Claude to list channels in your server
3. Ask Claude to send a test message to a channel

If you see errors:
- Double-check your bot token is correct
- Verify the bot is in your server
- Ensure privileged intents are enabled in Developer Portal

## Usage

Once configured, Claude can interact with your Discord server using these tools:

### `discord_discover`
Browse all available operations organized by category.

### `discord_get_schema`
Get detailed parameter schema for a specific operation.

```
discord_get_schema("messages.send")
```

### `discord_execute`
Execute an operation with parameters.

```
discord_execute("messages.send", {
  "channel_id": "123456789",
  "content": "Hello from Claude!"
})
```

## Operation Categories

| Category | Operations | Description |
|----------|------------|-------------|
| messages | 9 | Send, read, edit, delete, pin messages |
| reactions | 5 | Add, remove, list reactions |
| threads | 10 | Create, manage, archive threads |
| channels | 7 | Create, edit, delete channels |
| members | 6 | List, search, edit members |
| moderation | 7 | Kick, ban, timeout members |
| roles | 5 | Create, edit, delete roles |
| invites | 4 | Create, list, delete invites |
| events | 6 | Scheduled event management |
| polls | 2 | Create and end polls |
| guild | 4 | Server settings and info |
| audit_log | 1 | View audit log |
| automod | 5 | Auto-moderation rules |
| webhooks | 7 | Webhook management |
| voice | 2 | Voice channel controls |
| emojis | 5 | Custom emoji management |
| stickers | 3 | Sticker management |
| forum | 5 | Forum posts and tags |
| stage | 6 | Stage channel instances |
| onboarding | 3 | New member onboarding |
| welcome_screen | 2 | Welcome screen settings |
| soundboard | 5 | Soundboard sounds |
| commands | 5 | Slash command management |
| integrations | 2 | Server integrations |
| widget | 3 | Server widget |
| vanity | 2 | Vanity URL |
| templates | 6 | Server templates |
| dm | 1 | Direct messages |
| bulk_ban | 1 | Bulk ban users |

## Examples

### Send a message
```
discord_execute("messages.send", {
  "channel_id": "1234567890",
  "content": "Hello, Discord!"
})
```

### Create a poll
```
discord_execute("polls.create", {
  "channel_id": "1234567890",
  "question": "What's your favorite color?",
  "answers": ["Red", "Blue", "Green"],
  "duration_hours": 24
})
```

### Timeout a member
```
discord_execute("moderation.timeout", {
  "user_id": "9876543210",
  "duration_seconds": 3600,
  "reason": "Breaking server rules"
})
```

### Create a scheduled event
```
discord_execute("events.create", {
  "name": "Community Meetup",
  "description": "Weekly community call",
  "start_time": "2025-01-25T18:00:00Z",
  "location": "https://meet.example.com"
})
```

## Security Best Practices

- **Never commit your bot token** to version control
- **Never share your bot token** publicly
- If your token is exposed, **reset it immediately** in the Developer Portal
- Use environment variables for sensitive configuration
- Grant only the permissions your bot actually needs
- The bot can only manage resources below its highest role in the hierarchy
- Review Discord's [Bot Best Practices](https://discord.com/developers/docs/topics/community-resources)

## Rate Limits

Discord enforces rate limits on API requests. This server handles rate limiting automatically, but be aware:
- Global limit: 50 requests/second
- Per-route limits vary by endpoint
- Bulk operations are more efficient than individual calls

## Troubleshooting

### "401 Unauthorized" errors
- Your bot token is incorrect or has been reset
- Get a new token from the Developer Portal

### "403 Forbidden" errors
- The bot lacks required permissions
- The bot's role is too low in the hierarchy to manage the target
- Check channel-specific permission overrides

### Bot appears offline
- The MCP server only connects when Claude makes requests (REST API, not Gateway)
- This is normal - the bot doesn't maintain a persistent connection

### Can't read message content
- Enable "Message Content Intent" in the Developer Portal Bot section
- This is required to read the text content of messages

### Can't list members
- Enable "Server Members Intent" in the Developer Portal Bot section
- This is required for member-related operations

### Bot can't manage a user/role
- The bot's highest role must be above the target user's highest role
- Bots cannot manage the server owner
- Check if there are channel-specific permission denies

## License

MIT License - see [LICENSE](LICENSE) for details.
