import base64
import hashlib
import logging
import re

logger = logging.getLogger(__name__)
import os
import os.path as path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import yt_dlp
from typing import Optional

from twitch_spy.media_downloader.atomizer import Atom


class VideoMetadata:
    def __init__(self, title: str, url: str) -> None:
        self.title = title
        self.url = url


def thumbnail_cache_name(thumbnail_name: str, youtube_video_url: str) -> str:
    video_key = hashlib.sha256(youtube_video_url.encode("utf-8")).hexdigest()[:12]
    return f"{safe_pathname(thumbnail_name)}__{video_key}"


def _is_corrupt_audio(filepath: str) -> bool:
    """Return True if the file is missing, empty, or Mutagen cannot parse it."""
    if not os.path.isfile(filepath):
        return True
    if os.path.getsize(filepath) == 0:
        return True
    try:
        audio = mutagen.File(filepath)
        return audio is None or audio.info is None or getattr(audio.info, "length", 0) <= 0
    except (OSError, mutagen.MutagenError):
        return True


class YoutubeDownloader:
    def __init__(self) -> None:
        pass

    @staticmethod
    def download_thumbnail(
        youtube_video_url: str, thumbnail_name: str, output_directory: str
    ) -> Optional[str]:
        thumbnails_dir = path.join(output_directory, "thumbnails")
        os.makedirs(thumbnails_dir, exist_ok=True)

        thumbnail_base = path.join(
            thumbnails_dir,
            thumbnail_cache_name(thumbnail_name, youtube_video_url),
        )
        thumbnail_path = thumbnail_base + ".jpg"
        if path.isfile(thumbnail_path):
            return thumbnail_path

        ydl_opts = {
            "skip_download": True,
            "writethumbnail": True,
            "quiet": True,
            "outtmpl": {
                "default": thumbnail_base + ".%(ext)s",
                "thumbnail": thumbnail_base + ".%(ext)s",
            },
            "postprocessors": [
                {
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                    "when": "before_dl",
                }
            ],
        }
        from twitch_spy import config
        if config.FFMPEG_LOCATION:
            ydl_opts["ffmpeg_location"] = config.FFMPEG_LOCATION
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_video_url, download=True)

        for thumbnail in reversed(info_dict.get("thumbnails") or []):
            downloaded_path = thumbnail.get("filepath")
            if downloaded_path and path.isfile(downloaded_path):
                return downloaded_path
        if path.isfile(thumbnail_path):
            return thumbnail_path
        return None

    @staticmethod
    def add_preview_picture_to_audio_file(
        thumbnail_path: Optional[str], audio_path: str
    ) -> Optional[str]:
        if thumbnail_path and path.isfile(thumbnail_path):
            print(f"Thumbnail found: {thumbnail_path}")
            audio = ID3(audio_path)
            with open(thumbnail_path, "rb") as thumbnail_file:
                audio["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=thumbnail_file.read(),
                )
            audio.save()
            return thumbnail_path
        else:
            print(f"Thumbnail not found: {thumbnail_path}")
            return None

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
    def download_audio(atom: Atom) -> str:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(atom.download_dir, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        from twitch_spy import config
        if config.FFMPEG_LOCATION:
            ydl_opts["ffmpeg_location"] = config.FFMPEG_LOCATION
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(atom.url, download=False)
            atom.content_title = info_dict.get("title") or atom.content_title
            filename = ydl.prepare_filename(info_dict)
            filename = path.abspath(filename)
            # Change the extension to mp3
            base = os.path.splitext(filename)[0]
            filename = base + ".mp3"

            if os.path.isfile(filename) and _is_corrupt_audio(filename):
                logger.warning(f"Removing corrupt file: {filename}")
                os.remove(filename)

            if not os.path.isfile(filename):
                # Clean up any leftover intermediate files (e.g. .webm from an interrupted download)
                # so yt-dlp doesn't skip them and can start fresh.
                for f in os.listdir(atom.download_dir):
                    f_base, f_ext = os.path.splitext(f)
                    if f_base == os.path.basename(base) and f_ext not in (".mp3", ".part"):
                        logger.warning(f"Removing leftover intermediate file: {f}")
                        os.remove(os.path.join(atom.download_dir, f))
                ydl.download([atom.url])
            else:
                logger.debug(f"File already exists, skipping download: {filename}")

            atom.media_file_os_path = filename  # Store media file path

            try:
                YoutubeDownloader.add_metadata_to_audio_file(info_dict, filename)
            except Exception as e:
                raise e
            try:
                thumbnail_path = YoutubeDownloader.download_thumbnail(
                    atom.url,
                    info_dict.get("title") or info_dict.get("id") or "thumbnail",
                    atom.download_dir,
                )
                thumbnail_path = YoutubeDownloader.add_preview_picture_to_audio_file(
                    thumbnail_path, filename
                )
                if thumbnail_path and path.exists(thumbnail_path):
                    with open(thumbnail_path, "rb") as f:
                        atom.thumbnail_image_in_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                raise e
            return filename

def get_playlist_video_urls(playlist_url: str) -> list[VideoMetadata]:
    with yt_dlp.YoutubeDL(
            {
                "ignoreerrors": True,
                "quiet": True,
                "extract_flat": True,
                "force_generic_extractor": True,
            }
    ) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)

    if not playlist_dict or "entries" not in playlist_dict:
        logger.warning("Could not extract playlist info for %s", playlist_url)
        return []

    res = []
    for video in playlist_dict["entries"]:
        if video is not None:
            video_id = video.get("id")
            video_title = video.get("title")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_metadata = VideoMetadata(title=video_title, url=video_url)
            res.append(video_metadata)
    return res


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


def get_video_title(video_url: str) -> Optional[str]:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        logger.warning("Could not extract title for %s: %s", video_url, exc)
        return None

    return info_dict.get("title") if info_dict else None


def safe_pathname(dir: str) -> str:
    # Replace any character that is not allowed in Windows filenames with an underscore
    return re.sub(r'[\\/:*?"<>| ]', "_", dir)


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract the playlist ID from the URL, or None if not present."""
    m = re.search(r"list=([\w-]+)", url)
    return m.group(1) if m else None


def get_playlist_download_directory(playlists_directory: str, playlist_url: str):
    def find_existing_directory(
            playlist_directory: str, playlist_id: str
    ) -> Optional[str]:
        """Search for an existing directory by playlist ID."""
        for entry in os.listdir(playlist_directory):
            entry_path = path.join(playlist_directory, entry)
            if path.isdir(entry_path) and playlist_id in entry:
                return entry_path
        return None

    playlist_id = extract_playlist_id(playlist_url)
    if not playlist_id:
        raise ValueError(f"No playlist ID found in URL: {playlist_url}")
    existing_dir = find_existing_directory(playlists_directory, playlist_id)
    if existing_dir:
        print(f"Found existing directory by project id: {playlist_id}")
        return existing_dir

    print(f"Downloads directory does not exist for {playlist_id}.")
    # print("Creating a new one.")
    playlist_title = get_playlist_name(playlist_url)
    playlist_dir = f"{safe_pathname(playlist_title)}_{playlist_id}"
    return path.join(playlists_directory, playlist_dir)
