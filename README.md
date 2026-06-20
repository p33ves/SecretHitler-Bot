# SecretHitler-Bot

Licensed under [Creative Commons BY-NC-SA](LICENSE)

A Discord bot moderator for [Secret Hitler](https://www.secrethitler.com) — the social deduction board game. Play with 5–10 friends directly in a Discord server text channel.

For game rules: <https://bit.ly/3f3JJF9>

---

## Setup

### Prerequisites

- Python 3.8 or newer
- A Discord bot application with a token ([Discord Developer Portal](https://discord.com/developers/applications))

### Install

```bash
git clone https://github.com/p33ves/SecretHitler-Bot.git
cd SecretHitler-Bot
pip install .
```

For development (includes linting, type-checking, and test tools):

```bash
pip install -e ".[dev]"
```

### Configure the bot token

Create `auth.json` in the project root:

```json
{ "token": "YOUR_BOT_TOKEN_HERE" }
```

> **Note:** `auth.json` is gitignored. Never commit your token.

### Run

```bash
python -m secret_hitler
```

---

## Discord Bot Permissions

### Privileged Gateway Intents

These must be enabled in the **Discord Developer Portal → Bot → Privileged Gateway Intents**:

| Intent | Why it's needed |
|---|---|
| **Message Content Intent** | Required to read command text (e.g. `sh!p @user`) |
| **Server Members Intent** | Required to look up member info for role assignment |

### Bot Permission Scopes

When generating an invite link via **OAuth2 → URL Generator**, select the `bot` scope and the following permissions:

| Permission | Why it's needed |
|---|---|
| Read Messages / View Channels | Receive commands in the game channel |
| Send Messages | Post game updates and responses |
| Embed Links | Send rich embeds for board state, votes, policies |
| Attach Files | Attach board/policy/role images to embeds |
| Read Message History | Edit the board-state message in place |

The bot also sends **Direct Messages** to each player (for role reveal and policy picks). Users must have DMs enabled from server members for the bot to reach them.

---

## Commands

All commands use the `sh!` prefix.

| Command | Description |
|---|---|
| `sh!test` | Check your connection to the bot |
| `sh!launch` | Open a game lobby in the current channel |
| `sh!join` | Join the open lobby |
| `sh!begin` | Start the game (game owner only) |
| `sh!p <@user \| policy>` | Pick a chancellor / discard or enact a policy / exercise a power |
| `sh!v ja\|nein` | Cast your vote during an election |
| `sh!see` | Peek the top 3 policy cards (when the power is active) |
| `sh!veto` | Veto the current policy draw (when the power is active) |
| `sh!reset` | Clear the active game from this channel |
| `sh!help` | List all valid commands |

---

## Repo Structure

```
src/secret_hitler/   Python package — bot logic, game state, board rendering
images/              PNG/JPG assets used for Discord embeds
tests/               pytest test suite for core game logic
pyproject.toml       Project metadata and dependencies
auth.json            Bot token (create locally, not committed)
```

---

## Known Issues

- **Discord mention format** — `sh!p @user` picks may silently fail on modern Discord clients. Discord API v9+ sends mentions as `<@USER_ID>` (no `!`), but the current parser checks for the older `<@!USER_ID>` format.
- **DM failures** — if a player has DMs from server members disabled, role and policy messages will fail silently. The game will stall at that point.
- **No game timeout** — a stalled or abandoned game must be cleared manually with `sh!reset`.

## Planned Improvements

- Auto-reset after a configurable inactivity timeout
- Graceful error message when the bot cannot DM a player
- `sh!status` command to display the current game phase on demand
- `sh!kick @user` for the game owner to remove a disconnected player
- Per-turn reminders for players who haven't responded
