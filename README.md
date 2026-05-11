# Megks Bot

A Discord bot built with `discord.py`, featuring music playback, moderation, and general utility commands. Greek-language interface.

## Features

- **Music** — YouTube playback with queue, shuffle, loop, skip, pause/resume
- **Moderation** — kick, ban, unban, mute, unmute, purge
- **General** — avatar, userinfo, help
- **Fun** — random choice picker
- **NSFW** — random image fetch (age-restricted channels only)
- **Dev** — hot-reload cogs without restarting (owner-only)

## Project Structure

```
megks_bot/
├── bot.py              # Entry point
├── config.py           # Loads token + prefix from .env
├── cogs/               # Feature modules
│   ├── general.py
│   ├── moderation.py
│   ├── music.py
│   ├── fun.py
│   ├── nsfw.py
│   └── dev.py
├── tests/              # pytest suite
├── Makefile            # Deploy + service commands
└── requirements.txt
```

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env with your DISCORD_TOKEN
python3 bot.py
```

System dependencies:
```bash
sudo apt install ffmpeg
```

## Tests

```bash
pytest
```

## Deployment (Raspberry Pi)

Configure deploy targets:
```bash
cp .env.deploy.example .env.deploy
# Edit with your Pi's user, host, path, and repo URL
```

First-time deployment:
```bash
make deploy
scp .env user@pi:~/megks_bot/.env
```

Create the systemd service at `/etc/systemd/system/megks_bot.service`:
```ini
[Unit]
Description=Megks Discord Bot
After=network.target

[Service]
User=dietpi
WorkingDirectory=/home/dietpi/megks_bot
ExecStart=/home/dietpi/megks_bot/venv/bin/python3 bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable megks_bot --now
```

## Makefile Commands

| Command | Description |
|---|---|
| `make test` | Run the test suite locally |
| `make deploy` | First-time clone + venv setup on the Pi |
| `make update` | Pull latest from git on Pi and restart the bot (push manually first) |
| `make start` | Start the bot service |
| `make stop` | Stop the bot service |
| `make restart` | Restart the bot service |
| `make status` | Show the bot service status |
| `make logs` | Stream live bot logs |
| `make enable` | Enable auto-start on boot |
| `make disable` | Disable auto-start on boot |

## Development Workflow

1. Edit code locally
2. Run `pytest` to verify tests pass
3. `git push` to GitHub
4. `make update` to deploy to the Pi

## Architecture Notes

- Cogs are auto-loaded from the `cogs/` directory on startup
- Each cog is a self-contained `commands.Cog` subclass with a `setup(bot)` function
- The `dev` cog allows hot-reloading cogs in production via `!reload <cogname>`
- The bot uses YouTube intent + Server Members intent + Message Content intent