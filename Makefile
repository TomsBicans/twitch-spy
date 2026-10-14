.PHONY: help install install-ffmpeg test lint frontend-build verify run_web run_api \
	build build-linux build-wsl build-windows build-all smoke smoke-linux \
	smoke-windows checksums artifacts clean-build next-version release-help \
	check-preview check-components check-library

BUILD := uv run python scripts/build.py
RELEASE := uv run python scripts/release.py
BUMP ?= patch
BROWSER_CHECK := uv run --with playwright python -m

help:
	@$(BUILD) --help
	@echo "make next-version [BUMP=patch|minor|major] - preview using local tags"
	@echo "make release-help - show release script commands"
	@echo "make check-preview - check the latest Windows build in Edge"
	@echo "make check-components / check-library - browser checks against running Vite"

check-preview:
	$(BROWSER_CHECK) tests.check_preview

check-components:
	$(BROWSER_CHECK) tests.check_components

check-library:
	$(BROWSER_CHECK) tests.check_library_browser

next-version:
	$(RELEASE) next-version --bump "$(BUMP)"

release-help:
	@$(RELEASE) --help

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
