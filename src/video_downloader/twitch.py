import os
import sys
import subprocess
import streamlink
import os.path as path
import datetime
import re
import traceback
import src.video_downloader.constants as const
import src.video_downloader.config as config


class TwitchDownloader:
    def __init__(self, ffmpeg_path=None):
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"

    @staticmethod
    def create_output_file_name(channel_url: str):
        # Extract the channel name from the channel URL
        match = re.search(r"twitch.tv/(\w+)", channel_url)
        if match:
            channel_name = match.group(1)
        else:
            raise ValueError("Invalid Twitch channel URL")

        # Create a unique output file name based on the channel name and current date/time
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"{channel_name}_{now}.mp4"

        return output_filename

    def download_stream_video(self, channel_url, download_directory: str):
        try:
            streams = streamlink.streams(channel_url)
            stream_options = streams.keys()
            stream = streams["best"]

            output_filename = self.create_output_file_name(channel_url)
            command = [
                self.ffmpeg_path,
                "-i",
                stream.url,
                "-c",
                "copy",
                "-bsf:a",
                "aac_adtstoasc",
                path.join(download_directory, output_filename),
            ]

            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE
            )
            process.communicate()
        except Exception as e:
            traceback.print_exc()
            print(f"An error occurred: {e}")

    def download_stream_audio(self, channel_url, download_directory: str):
        try:
            streams = streamlink.streams(channel_url)
            stream_options = streams.keys()
            stream = streams["best"]

            output_filename = self.create_output_file_name(channel_url)
            audio_output_filename = output_filename.replace(".mp4", ".mp3")

            command = [
                self.ffmpeg_path,
                "-i",
                stream.url,
                "-vn",  # No video
                "-c:a",  # Codec for audio
                "libmp3lame",  # Use the LAME MP3 encoder
                "-q:a",  # Audio quality
                "2",  # Set audio quality (0 - 9, where 0 is the best quality and 9 is the worst)
                path.join(download_directory, audio_output_filename),
            ]

            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE
            )
            process.communicate()
        except Exception as e:
            traceback.print_exc()
            print(f"An error occurred: {e}")


def process_twitch_url(url: str, mode: const.CONTENT_MODE) -> const.PROCESS_STATUS:
    print("Twitch url detected.")
    downloader = TwitchDownloader()
    ttv_streams = path.join(config.STREAM_DOWNLOADS, "twitch_streams")
    config.create_directory_if_not_exists(ttv_streams)
    print(f"Starting twitch stream download: {url}")
    downloader.download_stream_audio(url, ttv_streams)
    return const.PROCESS_STATUS.SUCCESS


if __name__ == "__main__":
    downloader = TwitchDownloader()
    downloader.download_stream_video(
        "https://www.twitch.tv/rawchixx", config.STREAM_DOWNLOADS
    )
