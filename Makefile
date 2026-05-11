# Load deploy config (PI_USER, PI_HOST, PI_DIR, REPO_URL) from .env.deploy
-include .env.deploy

.PHONY: test deploy update start stop restart status logs enable disable

# Run the test suite locally
test:
	pytest

# First-time setup on the Pi: clone repo, create venv, install dependencies
deploy:
	ssh $(PI_USER)@$(PI_HOST) "git clone $(REPO_URL) $(PI_DIR) && cd $(PI_DIR) && python3 -m venv venv && venv/bin/pip install -r requirements.txt"

# Pull latest changes on the Pi and restart the bot (push to git first manually)
update:
	ssh $(PI_USER)@$(PI_HOST) "cd $(PI_DIR) && git pull && sudo systemctl restart megks_bot"

# Start the bot service on the Pi
start:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl start megks_bot"

# Stop the bot service on the Pi
stop:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl stop megks_bot"

# Restart the bot service on the Pi
restart:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl restart megks_bot"

# Show the current status of the bot service
status:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl status megks_bot"

# Stream the bot's live logs (Ctrl+C to exit)
logs:
	ssh $(PI_USER)@$(PI_HOST) "sudo journalctl -u megks_bot -f"

# Enable the bot to auto-start on boot
enable:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl enable megks_bot"

# Disable auto-start on boot (does not stop the running service)
disable:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl disable megks_bot"
