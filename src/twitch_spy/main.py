import logging
import time
import threading
import webbrowser
import subprocess
import sys

if sys.stderr is not None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    # Parse args and init config before importing app so that all downstream
    # modules (system_logger, storage_manager, etc.) see the correct paths.
    from twitch_spy import cli
    args = cli.parse_args()

    import twitch_spy.config as config
    from twitch_spy.desktop import InstanceLock, bundled_adb, bundled_ffmpeg, open_when_ready, select_port, user_data_dir

    output_dir = args.output_dir or str(user_data_dir())
    adb_exe = args.adb_exe or bundled_adb()
    ffmpeg_location = args.ffmpeg_location or bundled_ffmpeg()
    if args.check_tools:
        subprocess.run([ffmpeg_location, "-version"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([adb_exe, "version"], check=True, stdout=subprocess.DEVNULL)
        return

    lock = InstanceLock(user_data_dir() / "instance.json")
    existing = lock.running_instance()
    if existing:
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
    config.init(output_dir, android_dest=args.android_dest, adb_exe=adb_exe, ffmpeg_location=ffmpeg_location)

    import twitch_spy.app as app

    try:
        if not args.no_browser:
            threading.Thread(target=open_when_ready, args=(url, webbrowser.open), daemon=True, name="browser-launcher").start()
        start_time = time.time()
        app.main(port=port, development=args.dev)
        logging.info("Program finished in %.2f seconds.", time.time() - start_time)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
