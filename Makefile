install:
	uv sync

install-ffmpeg:
	sudo apt update -y && sudo apt install ffmpeg -y

run_web:
	cd client && npm run dev

run_api:
	uv run twitch-spy --output-dir ./data

format:
	cd client && npm run format