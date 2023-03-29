import re
import os
from mutagen.mp3 import MP3
from mutagen.wavpack import WavPack
from tqdm import tqdm
import os.path as path


def safe_pathname(dir: str) -> str:
    # Replace any character that is not allowed in Windows filenames with an underscore
    return re.sub(r'[\\/:*?"<>| ]', "_", dir)


def format_duration(duration):
    # Convert total duration in seconds to hours, minutes, and remaining seconds
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format duration as string
    duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    return duration_str


def count_songs_and_duration(directory: str):
    """returns (total songs, total duration (s))"""
    total_songs = 0
    total_duration = 0

    for root, dirs, files in tqdm(os.walk(directory)):
        for file in files:
            try:
                if file.endswith(".mp3"):
                    # Count song
                    total_songs += 1

                    # Get song duration
                    filepath = os.path.join(root, file)
                    audio = MP3(filepath)
                    total_duration += audio.info.length

                elif file.endswith(".wav"):
                    # Count song
                    total_songs += 1

                    # Get song duration
                    filepath = os.path.join(root, file)
                    audio = WavPack(filepath)
                    total_duration += audio.info.length
            except:
                print(f"Error analyzing this file: {path.abspath(file)}")

    return total_songs, total_duration
