import pytube
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import os.path as path
import re
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import requests

import googleapiclient.discovery
import re


def safe_pathname(dir: str) -> str:
    # Replace any character that is not allowed in Windows filenames with an underscore
    return re.sub(r'[\\/:*?"<>| ]', "_", dir)


class Utils:
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_highest_bitrate_audio_stream(yt: pytube.YouTube) -> pytube.Stream:
        return yt.streams.filter(only_audio=True).order_by("abr").desc().first()

    @staticmethod
    def download_stream(stream: pytube.Stream, output_directory: str) -> str:
        filename = stream.download(output_path=output_directory)
        return filename

    @staticmethod
    def convert_to_mp3_extension(filename: str) -> str:
        base, ext = os.path.splitext(filename)
        audio = AudioFileClip(filename)
        new_filename = base + ".mp3"
        if os.path.exists(new_filename):
            os.remove(new_filename)
        audio.write_audiofile(new_filename)
        os.remove(filename)
        return new_filename

    @staticmethod
    def add_metadata_to_audio_file(yt: pytube.YouTube, filename: str) -> None:
        try:
            audio = EasyID3(filename)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(filename, easy=True)
            audio.add_tags()
        audio["title"] = yt.title
        audio["artist"] = yt.author
        audio["album"] = "YouTube Audio"
        # audio["rating"] = yt.rating
        audio.save()

    @staticmethod
    def add_preview_picture_to_audio_file(yt: pytube.YouTube, filename: str) -> None:
        thumbnail_url = yt.thumbnail_url
        if not thumbnail_url:
            print("Using google API")
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", developerKey="AIzaSyCtvDiw629vvfQr84XQGjY8seKfFSuInVg"
            )
            video_id = yt.video_id
            response = youtube.videos().list(part="snippet", id=video_id).execute()
            thumbnails = response["items"][0]["snippet"]["thumbnails"]
            if "maxres" in thumbnails:
                thumbnail_url = thumbnails["maxres"]["url"]
            elif "high" in thumbnails:
                thumbnail_url = thumbnails["high"]["url"]
            elif "medium" in thumbnails:
                thumbnail_url = thumbnails["medium"]["url"]
        if thumbnail_url:
            print(f"Thumbnail found: {thumbnail_url}")
            download_dir = path.dirname(filename)
            thumbnails_dir = path.join(download_dir, "thumbnails")
            if not path.exists(thumbnails_dir):
                os.mkdir(thumbnails_dir)
            thumbnail_loc = path.join(thumbnails_dir, safe_pathname(yt.title) + ".jpg")
            with open(thumbnail_loc, "wb") as thumbnail_file:
                thumbnail_file.write(requests.get(thumbnail_url).content)
            audio = ID3(filename)
            with open(thumbnail_loc, "rb") as thumbnail_file:
                audio["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=thumbnail_file.read(),
                )
            audio.save()
        else:
            print(f"Thumbnail not found: {yt}")


class YoutubeDownloader:
    def __init__(self) -> None:
        pass

    @staticmethod
    def download_video(url: str, output_directory: str) -> str:
        # Create a YouTube object
        yt = pytube.YouTube(url)

        # Get the first stream with the highest resolution
        stream = (
            yt.streams.filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )

        # Download the video
        return stream.download(output_path=output_directory)

    @staticmethod
    def download_audio(url: str, output_directory: str) -> str:
        yt = pytube.YouTube(url)
        stream = Utils.get_highest_bitrate_audio_stream(yt)
        filename = Utils.download_stream(stream, output_directory)
        new_filename = Utils.convert_to_mp3_extension(filename)
        try:
            Utils.add_metadata_to_audio_file(yt, new_filename)
        except Exception as e:
            raise e
        try:
            Utils.add_preview_picture_to_audio_file(yt, new_filename)
        except Exception as e:
            raise e
        return new_filename

    @staticmethod
    def convert_to_mp3(video_path: str):
        # Open the video file
        video = VideoFileClip(video_path)

        # Extract the audio
        audio = video.audio

        # Create the output filename
        output_filename = video_path.replace(".mp4", ".mp3")

        # Write the audio to the output file
        audio.write_audiofile(output_filename)

        # Set the filename to the output filename
        return output_filename

    def download_and_convert(self, url: str, output_directory: str):
        print("Downloading video...")
        video_path = self.download_video(url, output_directory)
        print("Converting video to mp3")
        return self.convert_to_mp3(video_path)


def get_playlist_video_urls(playlist_url: str) -> list[str]:
    playlist = pytube.Playlist(playlist_url)
    return playlist.video_urls


def get_playlist_name(playlist_url):
    playlist = pytube.Playlist(playlist_url)
    return playlist.title()


def safe_pathname(dir: str) -> str:
    # Replace any character that is not allowed in Windows filenames with an underscore
    return re.sub(r'[\\/:*?"<>| ]', "_", dir)


def get_playlist_download_directory(downloads_dir: str, playlist_url: str):
    # playlist_id = re.search(r"list=(\w+)", playlist_url).group(1)
    playlist_id = re.search(r"list=([\w-]+)", playlist_url).group(1)

    for entry in os.listdir(downloads_dir):
        entry_path = path.join(downloads_dir, entry)
        if path.isdir(entry_path) and playlist_id in entry:
            print(f"Found existing directory by project id: {playlist_id}")
            return entry_path

    print(f"Downloads directory does not exist for {playlist_id}. Creating a new one.")
    playlist_title = get_playlist_name(playlist_url)
    playlist_dir = f"{safe_pathname(playlist_title)}_{playlist_id}"
    return path.join(downloads_dir, playlist_dir)


def is_youtube_playlist(url: str) -> bool:
    if "youtube.com/playlist" in url:
        return True
    else:
        return False


def is_youtube_video(url: str) -> bool:
    if "youtube.com/watch?v=" in url or "youtu.be/" in url:
        return True
    else:
        return False


if __name__ == "__main__":
    video = YoutubeDownloader("https://www.youtube.com/watch?v=YJVmu6yttiw")
    video.download_and_convert()
