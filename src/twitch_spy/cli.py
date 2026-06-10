import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class SystemConfiguration:
    output_dir: str
    android_dest: str


def parse_args() -> SystemConfiguration:
    parser = argparse.ArgumentParser(
        description="Manage a local music library populated from YouTube"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data",
        help="Directory for logs and stream downloads (default: ./data)",
    )
    parser.add_argument(
        "--android-dest",
        type=str,
        default="/sdcard/SdCardBackup/Music",
        help="Android destination root path for sync (default: /sdcard/SdCardBackup/Music)",
    )
    args = parser.parse_args()
    return SystemConfiguration(args.output_dir, args.android_dest)
