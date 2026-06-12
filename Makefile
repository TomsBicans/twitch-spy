.PHONY: help install install-ffmpeg test lint frontend-build verify run_web run_api \
	build build-linux build-wsl build-windows build-all smoke smoke-linux \
	smoke-windows checksums artifacts clean-build

BUILD := uv run python scripts/build.py

help:
	@$(BUILD) --help

install:
	uv sync

install-ffmpeg:
	sudo apt update -y && sudo apt install ffmpeg -y

test:
	uv run pytest -v

lint:
	cd client && npm run lint

frontend-build:
	cd client && npm run build

verify:
	$(BUILD) verify

run_web:
	cd client && npm run dev

run_api:
	uv run twitch-spy --output-dir ./data --android-dest /sdcard/SdCardBackup/Music --port 5000 --no-browser --dev

build:
	$(BUILD) build

build-linux:
	$(BUILD) build --target linux

build-wsl: build-linux

build-windows:
	$(BUILD) build --target windows

build-all:
	$(BUILD) build --target all

smoke:
	$(BUILD) smoke --target all

smoke-linux:
	$(BUILD) smoke --target linux

smoke-windows:
	$(BUILD) smoke --target windows

checksums:
	$(BUILD) checksums --target all

artifacts:
	$(BUILD) artifacts

clean-build:
	$(BUILD) clean
