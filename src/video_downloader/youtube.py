import pytube
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import os.path as path
import re
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import requests
import yt_dlp
import googleapiclient.discovery
import re


class Utils:
    def __init__(self) -> None:
        pass

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


class YoutubeDownloader:
    def __init__(self) -> None:
        pass

    @staticmethod
    def add_preview_picture_to_audio_file(info_dict: dict, filepath: str) -> None:
        thumbnail_url = info_dict.get("thumbnail", None)
        if not thumbnail_url:
            print("Using google API")
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", developerKey="AIzaSyCtvDiw629vvfQr84XQGjY8seKfFSuInVg"
            )
            video_id = info_dict.get("id", None)
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
            download_dir = path.dirname(filepath)
            thumbnails_dir = path.join(download_dir, "thumbnails")
            if not path.exists(thumbnails_dir):
                os.mkdir(thumbnails_dir)
            thumbnail_loc = path.join(
                thumbnails_dir, safe_pathname(info_dict.get("title", None)) + ".jpg"
            )
            with open(thumbnail_loc, "wb") as thumbnail_file:
                thumbnail_file.write(requests.get(thumbnail_url).content)
            audio = ID3(filepath)
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
            print(f"Thumbnail not found: {info_dict.get('url', None)}")

    @staticmethod
    def add_metadata_to_audio_file(info_dict: dict, filepath: str) -> None:
        try:
            audio = EasyID3(filepath)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(filepath, easy=True)
            audio.add_tags()
        if info_dict.get("title", None):
            audio["title"] = info_dict.get("title", None)
        if info_dict.get("artist", None):
            audio["artist"] = info_dict.get("artist", None)
        if info_dict.get("album", None):
            audio["album"] = info_dict.get("album", None)
        audio.save()

    @staticmethod
    def download_video(url: str, output_directory: str) -> str:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(output_directory, "%(title)s.%(ext)s"),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename

    @staticmethod
    def download_audio(url: str, output_directory: str) -> str:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(output_directory, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            filename = path.abspath(filename)
            # Change the extension to mp3
            base = os.path.splitext(filename)[0]
            filename = base + ".mp3"

            try:
                YoutubeDownloader.add_metadata_to_audio_file(info_dict, filename)
            except Exception as e:
                raise e
            try:
                YoutubeDownloader.add_preview_picture_to_audio_file(info_dict, filename)
            except Exception as e:
                raise e
            return filename

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
    with yt_dlp.YoutubeDL({"ignoreerrors": True, "quiet": True}) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)

    video_urls = []
    for video in playlist_dict["entries"]:
        if video is not None:
            video_id = video.get("id")
            video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

    return video_urls


def get_playlist_name(playlist_url: str) -> str:
    with yt_dlp.YoutubeDL({"ignoreerrors": True, "quiet": True}) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)

    return playlist_dict.get("title")


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
