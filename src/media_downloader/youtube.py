import re
import traceback
import os
import os.path as path
import re
import requests
import mutagen
from moviepy.editor import VideoFileClip, AudioFileClip
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import yt_dlp
import googleapiclient.discovery
import src.media_downloader.constants as const
import config

# import src.video_downloader.config as config
from src.media_downloader.storage_manager import StorageManager


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

    @staticmethod
    def audio_length(audio_file: str) -> float:
        # Load the audio or video file with moviepy
        if audio_file.endswith(".mp4"):
            clip = VideoFileClip(audio_file)
        else:
            clip = AudioFileClip(audio_file)

        # Return the duration in seconds
        return float(clip.duration)

    @staticmethod
    def create_subdir_for_video_split(audio_file: str) -> str:
        save_dir = Utils.filepath_without_extension(audio_file)
        save_dir = path.join(
            path.dirname(save_dir), safe_pathname(path.basename(save_dir))
        )
        if not path.exists(save_dir):
            os.mkdir(save_dir)
        return save_dir

    @staticmethod
    def filepath_without_extension(filepath: str) -> str:
        return os.path.splitext(filepath)[0]

    @staticmethod
    def baseline_timestamp_pairs(timestamp_title_pairs: list, audio_length: float):
        """The incoming data is tuples with 3 elements, but they are not always in the same order.
        Return a list of tuples with this data (title, start_time, end_time)"""

        def time_to_seconds(time_str):
            """Convert a time string in HH:MM:SS or HH:MM format to seconds."""
            parts = list(map(int, time_str.split(":")))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            else:
                raise ValueError(f"Invalid time format: {time_str}")

        normalized_pairs = []
        for pair in timestamp_title_pairs:
            # Check if the potential time fields are indeed times by trying to convert them to seconds
            try:
                start_time = time_to_seconds(pair[1])
                end_time = time_to_seconds(pair[2])
                # If the above lines do not raise an exception, then the order is correct
                normalized_pairs.append((pair[0], start_time, end_time))
            except ValueError:
                # If an exception is raised, the order is incorrect and needs to be swapped
                start_time = time_to_seconds(pair[0])
                end_time = time_to_seconds(pair[1])
                normalized_pairs.append((pair[2], start_time, end_time))
        return normalized_pairs

    @staticmethod
    def split_file_by_tracks(youtube_url: str, audio_file: str):
        # Use yt-dlp to extract the video description and top comments
        ydl_opts = {"writecomments": True, "ignoreerrors": True, "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)

        description = info_dict.get("description", "")
        comments = info_dict.get("comments", [])

        # Combine the description and the text of the top 40 comments into one string
        text = description + "\n".join(comment["text"] for comment in comments[:40])

        # List of possible regular expressions
        regexes = [
            r"(.+?): (\d{1,2}:\d{2}(?:\:\d{2})?) - (\d{1,2}:\d{2}(?:\:\d{2})?)",  # Title: HH:MM(:SS) - HH:MM(:SS)
            r"(\d{1,2}:\d{2}(?:\:\d{2})?) (.+)",  # HH:MM(:SS) Title
            # Add more regular expressions if needed
        ]

        # Choose the regex that gives the most matches
        best_regex = max(regexes, key=lambda r: len(re.findall(r, text)))
        timestamp_title_pairs = re.findall(best_regex, text)
        print(timestamp_title_pairs)
        timestamp_title_pairs = Utils.baseline_timestamp_pairs(
            timestamp_title_pairs, Utils.audio_length(audio_file)
        )
        thumbnail_url = YoutubeDownloader.get_thumbnail_url(youtube_url)
        print(timestamp_title_pairs)

        # Load the audio file with moviepy
        audio = AudioFileClip(audio_file)
        for title, start_time, end_time in timestamp_title_pairs:
            # Use moviepy to cut the audio segment
            chunk = audio.subclip(start_time, end_time)
            save_dir = Utils.create_subdir_for_video_split(audio_file)
            save_location = path.join(save_dir, f"{title}.mp3")
            print(save_location)
            # Save each chunk as a separate audio file
            chunk.write_audiofile(save_location)
            Utils.add_title_to_audio_file(title, save_location)
            YoutubeDownloader.add_preview_picture_to_audio_file(
                title, thumbnail_url, save_location
            )

    @staticmethod
    def add_title_to_audio_file(title: str, filepath: str) -> None:
        try:
            audio = EasyID3(filepath)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(filepath, easy=True)
            audio.add_tags()
        audio["title"] = title
        audio.save()

    @staticmethod
    def add_artist_to_audio_file(artist: str, filepath: str) -> None:
        try:
            audio = EasyID3(filepath)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(filepath, easy=True)
            audio.add_tags()
        audio["artist"] = artist
        audio.save()

    @staticmethod
    def add_album_to_audio_file(album: str, filepath: str) -> None:
        try:
            audio = EasyID3(filepath)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.File(filepath, easy=True)
            audio.add_tags()
        audio["album"] = album
        audio.save()


class YoutubeDownloader:
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_thumbnail_url(youtube_video_url: str) -> str:
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_video_url, download=False)

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
        return thumbnail_url

    @staticmethod
    def add_preview_picture_to_audio_file(
        thumbnail_name: str, thumbnail_url: str, audio_path: str
    ) -> None:
        if thumbnail_url:
            print(f"Thumbnail found: {thumbnail_url}")
            download_dir = path.dirname(audio_path)
            thumbnails_dir = path.join(download_dir, "thumbnails")
            if not path.exists(thumbnails_dir):
                os.mkdir(thumbnails_dir)
            thumbnail_loc = path.join(
                thumbnails_dir, safe_pathname(thumbnail_name) + ".jpg"
            )
            with open(thumbnail_loc, "wb") as thumbnail_file:
                thumbnail_file.write(requests.get(thumbnail_url).content)
            audio = ID3(audio_path)
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
            print(f"Thumbnail not found: {thumbnail_url}")

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
            info_dict = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info_dict)
            filename = path.abspath(filename)
            # Change the extension to mp3
            base = os.path.splitext(filename)[0]
            filename = base + ".mp3"

            if not os.path.isfile(filename):
                ydl.download([url])  # Download the file here
            else:
                print(f"File already exists. {filename}")
                return filename

            try:
                YoutubeDownloader.add_metadata_to_audio_file(info_dict, filename)
            except Exception as e:
                raise e
            try:
                thumbnail_url = YoutubeDownloader.get_thumbnail_url(url)
                YoutubeDownloader.add_preview_picture_to_audio_file(
                    info_dict.get("title", None), thumbnail_url, filename
                )
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
    with yt_dlp.YoutubeDL(
        {
            "ignoreerrors": True,
            "quiet": True,
            "extract_flat": True,
            "force_generic_extractor": True,
        }
    ) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)

    video_urls = []
    for video in playlist_dict["entries"]:
        if video is not None:
            video_id = video.get("id")
            video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

    return video_urls


def get_playlist_name(playlist_url: str) -> str:
    ydl_opts = {
        "ignoreerrors": True,
        "quiet": True,
        "extract_flat": True,
        "extractor_args": [
            "youtube:skip:video_list"
        ],  # skip fetching details of individual videos
        "skip_download": True,  # make sure no downloading happens
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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


def process_youtube_url(url: str, mode: const.CONTENT_MODE) -> const.PROCESS_STATUS:
    downloader = YoutubeDownloader()
    if is_youtube_playlist(url):
        return process_youtube_playlist(url, downloader, mode)
    elif is_youtube_video(url):
        return process_youtube_video(url, downloader, mode)
    else:
        print("Invalid YouTube URL.")
        return const.PROCESS_STATUS.FAILED


def process_youtube_playlist(
    url: str, downloader: YoutubeDownloader, mode: const.CONTENT_MODE
) -> const.PROCESS_STATUS:
    print(f"Playlist detected: {url}")
    videos = get_playlist_video_urls(url)
    print(f"Got {len(videos)} videos.")
    if mode == const.CONTENT_MODE.AUDIO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "audio_library")
    elif mode == const.CONTENT_MODE.VIDEO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "video_library")
    download_dir = get_playlist_download_directory(download_dir, url)
    download_dir = config.create_directory_if_not_exists(download_dir)
    storage_manager = StorageManager(download_dir)
    for i, vid in enumerate(videos):
        print(f"Processing: {i+1}/{len(videos)} ...")
        if const.stop_workers.is_set():
            print("Stop workers flag is set. Exiting...")
            return const.PROCESS_STATUS.CANCELLED
        if storage_manager.already_downloaded(vid):
            print(f"Video already exists. Will skip download: {vid}")
            continue
        if mode == const.CONTENT_MODE.AUDIO:
            download_audio(downloader, download_dir, storage_manager, vid)
        elif mode == const.CONTENT_MODE.VIDEO:
            download_video(downloader, download_dir, storage_manager, url)
    return const.PROCESS_STATUS.SUCCESS


def download_audio(
    downloader: YoutubeDownloader,
    download_dir: str,
    storage_manager: StorageManager,
    url: str,
):
    try:
        print(f"Downloading {url} ...")
        audio_file = downloader.download_audio(url, download_dir)
        print(audio_file)
        with storage_manager.lock:
            storage_manager.mark_successful_download(url)
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_download(url)
        traceback.print_exc()
        return

    try:
        print(f"Splitting {audio_file} ...")
        split_length_criteria = 60 * 180  # 180 minutes
        if Utils.audio_length(audio_file) > (split_length_criteria):
            print(
                f"Video is longer than {split_length_criteria} seconds. Splitting video."
            )
            Utils.split_file_by_tracks(url, audio_file)
        else:
            print(
                f"Video is not longer than {split_length_criteria} seconds. Doing nothing."
            )
            return
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_split(url)
        traceback.print_exc()


def download_video(
    downloader: YoutubeDownloader,
    download_dir: str,
    storage_manager: StorageManager,
    url: str,
):
    try:
        print(f"Downloading {url} ...")
        audio_file = downloader.download_video(url, download_dir)
        print(audio_file)
        with storage_manager.lock:
            storage_manager.mark_successful_download(url)
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_download(url)
        traceback.print_exc()
        return

    try:
        print(f"Splitting {audio_file} ...")
        split_length_criteria = 60 * 180  # 180 minutes
        if Utils.audio_length(audio_file) > (split_length_criteria):
            print(
                f"Video is longer than {split_length_criteria} seconds. Splitting video."
            )
            Utils.split_file_by_tracks(url, audio_file)
        else:
            print(
                f"Video is not longer than {split_length_criteria} seconds. Doing nothing."
            )
            return
    except Exception as e:
        with storage_manager.lock:
            storage_manager.troublesome_split(url)
        traceback.print_exc()


def process_youtube_video(
    url: str, downloader: YoutubeDownloader, mode: const.CONTENT_MODE
) -> const.PROCESS_STATUS:
    print(f"Video detected: {url}")
    if mode == const.CONTENT_MODE.AUDIO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "audio_library")
        download_dir = path.join(download_dir, "random_audio")
        download_dir = config.create_directory_if_not_exists(download_dir)
        storage_manager = StorageManager(download_dir)
        download_audio(downloader, download_dir, storage_manager, url)
    elif mode == const.CONTENT_MODE.VIDEO:
        download_dir = path.join(config.STREAM_DOWNLOADS, "video_library")
        download_dir = path.join(download_dir, "random_videos")
        download_dir = config.create_directory_if_not_exists(download_dir)
        storage_manager = StorageManager(download_dir)
        download_video(downloader, download_dir, storage_manager, url)
    return const.PROCESS_STATUS.SUCCESS


if __name__ == "__main__":
    video = YoutubeDownloader("https://www.youtube.com/watch?v=YJVmu6yttiw")
    video.download_and_convert()
