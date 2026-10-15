import logging
import time
import threading
import webbrowser
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from twitch_spy.startup import StartupProgress

if sys.stderr is not None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main() -> None:
    from twitch_spy.startup import StartupProgress

    progress = StartupProgress()
    try:
        _run(progress)
    finally:
        progress.close()


def _run(progress: "StartupProgress") -> None:
    # Parse args and init config before importing app so that all downstream
    # modules (system_logger, storage_manager, etc.) see the correct paths.
    from twitch_spy import cli
    args = cli.parse_args()
    if args.no_browser or args.check_tools:
        progress.close()
    progress.update("Loading desktop settings...")

    import twitch_spy.config as config
    from twitch_spy.desktop import InstanceLock, bundled_adb, bundled_ffmpeg, select_port, user_data_dir, wait_until_ready

    output_dir = args.output_dir or str(user_data_dir())
    if args.check_tools:
        adb_exe = args.adb_exe or bundled_adb()
        ffmpeg_location = args.ffmpeg_location or bundled_ffmpeg()
        subprocess.run([ffmpeg_location, "-version"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([adb_exe, "version"], check=True, stdout=subprocess.DEVNULL)
        return

    lock = InstanceLock(user_data_dir() / "instance.json")
    existing = lock.running_instance()
    if existing:
        progress.update("Opening the running application...")
        if not args.no_browser:
            webbrowser.open(existing.url)
        return

    port = select_port(args.port)
    url = f"http://127.0.0.1:{port}"
    existing = lock.acquire(url)
    if existing:
        if not args.no_browser:
            webbrowser.open(existing.url)
        return
    tray = None
    try:
        progress.update("Locating bundled media tools...")
        adb_exe = args.adb_exe or bundled_adb()
        ffmpeg_location = args.ffmpeg_location or bundled_ffmpeg()
        config.init(output_dir, android_dest=args.android_dest, adb_exe=adb_exe, ffmpeg_location=ffmpeg_location)
        progress.update("Loading application modules...")
        import twitch_spy.app as app
        from pathlib import Path
        from twitch_spy.tray import DesktopTray, tray_enabled

        progress.update("Preparing your music library...")
        application = app.Application(development=args.dev)
        browser_url = "http://localhost:5173" if args.dev else url
        if tray_enabled(args.tray):
            tray = DesktopTray(browser_url, Path(config.LOG_DIR), application.request_shutdown)
            application.keep_running = tray.start()
        def finish_startup() -> None:
            if not wait_until_ready(url):
                logging.error("Startup timed out waiting for %s", url)
                progress.update("Startup is taking longer than expected. Check application.log.")
                return
            logging.getLogger("ApplicationLogger").info(
                "Application ready after %.2fs of Python startup",
                time.perf_counter() - progress.started,
            )
            try:
                if not args.no_browser:
                    progress.update("Opening your browser...")
                    if not webbrowser.open(browser_url):
                        logging.warning("Could not open browser automatically: %s", browser_url)
            finally:
                progress.close()

        progress.update("Starting the local server...")
        threading.Thread(target=finish_startup, daemon=True, name="browser-launcher").start()
        start_time = time.time()
        application.main_web(port=port)
        logging.info("Program finished in %.2f seconds.", time.time() - start_time)
    finally:
        if tray is not None:
            tray.stop()
        lock.release()


if __name__ == "__main__":
    main()
