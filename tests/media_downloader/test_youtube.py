import pytest
import src.media_downloader.youtube as youtube
from typing import List


PLAYLIST_URLS = [
    "https://www.youtube.com/playlist?list=PLCgSXQYoBb41x3JaoF9vlpQ7Yo9oIHqqN",
    "https://www.youtube.com/playlist?app=desktop&list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
]


@pytest.mark.parametrize("playlist", PLAYLIST_URLS)
def test_youtube_playlist_videos(playlist):
    videos = youtube.get_playlist_video_urls(playlist)
    # Assuming function should at least return a list (even if it's empty)
    test = [isinstance(it, youtube.VideoMetadata) for it in videos]
    assert all(test)

    # Optionally, if you know there should be videos:
    assert len(videos) > 0


@pytest.mark.parametrize("playlist", PLAYLIST_URLS)
def test_youtube_playlist_title(playlist):
    title = youtube.get_playlist_name(playlist)
    # Assuming function should return a non-empty string
    assert isinstance(title, str)
    assert title  # This checks if the string is non-empty
