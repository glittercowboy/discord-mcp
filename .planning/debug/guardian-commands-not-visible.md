---
status: verifying
trigger: "guardian-commands-not-visible"
created: 2026-01-23T13:30:00Z
updated: 2026-01-23T13:30:00Z
---

## Current Focus

hypothesis: CommandTree created as standalone object but never bound to Client
test: Check if tree is set as client.tree attribute
expecting: tree exists as global variable but not attached to client instance
next_action: Verify client.tree assignment and test fix

## Symptoms

expected: Typing /guardian in Discord shows autocomplete with status, config, verify, exempt subcommands
actual: Nothing appears - command not recognized
errors: None visible. Railway logs show "Synced slash commands to GSD: Get Shit Done" successfully
reproduction: Type /guardian in Discord
started: Just deployed. Never worked.

## Eliminated

## Evidence

- timestamp: 2026-01-23T13:32:00Z
  checked: guardian.py lines 27-34
  found: CommandTree created globally (line 30), GuardianCommands instantiated and added via tree.add_command() (lines 33-34)
  implication: Commands ARE registered to the tree before sync - registration looks correct

- timestamp: 2026-01-23T13:33:00Z
  checked: guardian.py lines 84-90 (on_ready sync)
  found: tree.sync(guild=guild) called per guild, logs "Synced slash commands to {guild.name}"
  implication: Sync is happening and succeeding (logs confirm this)

- timestamp: 2026-01-23T13:34:00Z
  checked: Discord bot setup pattern
  found: Using discord.Client instead of commands.Bot or discord.ext.commands.Bot
  implication: discord.Client doesn't have built-in command tree support - tree is created separately

- timestamp: 2026-01-23T13:40:00Z
  checked: Discord.py documentation and examples
  found: When using discord.Client, CommandTree must be assigned to client.tree attribute (not just standalone variable)
  implication: The tree variable is never connected to the client - Discord doesn't know about it

## Resolution

root_cause: CommandTree created as standalone global variable (line 30) but never assigned to client.tree attribute. Discord.py requires CommandTree to be at client.tree for it to work properly. The sync call succeeds but syncs nothing because Discord can't find the commands on the client instance.
fix: Changed `tree = app_commands.CommandTree(client)` to `client.tree = app_commands.CommandTree(client)` and updated all references from `tree` to `client.tree`
verification: Deploy to Railway and test /guardian command in Discord
files_changed: [src/guardian/guardian.py]

root_cause:
fix:
verification:
files_changed: []
