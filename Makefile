-include .env.deploy

.PHONY: test deploy update restart logs

test:
	pytest

deploy:
	ssh $(PI_USER)@$(PI_HOST) "git clone $(REPO_URL) $(PI_DIR) && cd $(PI_DIR) && python3 -m venv venv && venv/bin/pip install -r requirements.txt"

update:
	git push
	ssh $(PI_USER)@$(PI_HOST) "cd $(PI_DIR) && git pull && sudo systemctl restart megks_bot"

restart:
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl restart megks_bot"

logs:
	ssh $(PI_USER)@$(PI_HOST) "sudo journalctl -u megks_bot -f"
