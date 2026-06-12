import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class SystemConfiguration:
    output_dir: str | None
    android_dest: str
    port: int | None
    no_browser: bool
    adb_exe: str | None
    ffmpeg_location: str | None
    check_tools: bool
    dev: bool


def parse_args() -> SystemConfiguration:
    parser = argparse.ArgumentParser(
        description="Manage a local music library populated from YouTube"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for logs and downloads (default: platform user data directory)",
    )
    parser.add_argument(
        "--android-dest",
        type=str,
        default="/sdcard/SdCardBackup/Music",
        help="Android destination root path for sync (default: /sdcard/SdCardBackup/Music)",
    )
    parser.add_argument("--port", type=int, default=None, help="Local HTTP port (default: select an available port)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the default browser")
    parser.add_argument("--adb-exe", default=None, help="Override the bundled adb executable")
    parser.add_argument("--ffmpeg-location", default=None, help="Override bundled FFmpeg")
    parser.add_argument("--check-tools", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable the Vite development origin on http://localhost:5173",
    )
    args = parser.parse_args()
    return SystemConfiguration(
        args.output_dir,
        args.android_dest,
        args.port,
        args.no_browser,
        args.adb_exe,
        args.ffmpeg_location,
        args.check_tools,
        args.dev,
    )
