import pytest
import src.media_downloader.atomizer as atomizer
import src.media_downloader.constants as const
import os.path as path


def test_determine_platform():
    assert (
        atomizer.Atom._determine_platform("https://twitch.tv/somechannel")
        == const.PLATFORM.TWITCH
    )
    assert (
        atomizer.Atom._determine_platform("https://youtube.com/watch?v=someID")
        == const.PLATFORM.YOUTUBE
    )
    assert (
        atomizer.Atom._determine_platform("https://youtu.be/someID")
        == const.PLATFORM.YOUTUBE
    )
    assert (
        atomizer.Atom._determine_platform("https://someotherwebsite.com/")
        == const.PLATFORM.UNDEFINED
    )


def test_is_single_item():
    assert atomizer.Atom._is_single_item("https://youtube.com/watch?v=someID") == True
    assert (
        atomizer.Atom._is_single_item(
            "https://youtube.com/watch?v=someID&list=someListID"
        )
        == False
    )
    assert atomizer.Atom._is_single_item("https://twitch.tv/somechannel") == True
    assert atomizer.Atom._is_single_item("https://someotherwebsite.com/") == True


def test_determine_download_dir():
    # Mock data
    base_download_dir = "/base/path"

    # For YouTube with single video
    atom = atomizer.Atom(
        "https://youtube.com/watch?v=someID",
        const.CONTENT_MODE.AUDIO,
        base_download_dir,
    )
    expected_path = path.join(base_download_dir, "audio_library", "random_audio")
    assert atom._determine_download_dir(atom.url, base_download_dir) == expected_path

    atom = atomizer.Atom(
        "https://youtube.com/watch?v=someID",
        const.CONTENT_MODE.VIDEO,
        base_download_dir,
    )
    expected_path = path.join(base_download_dir, "video_library", "random_videos")
    assert atom._determine_download_dir(atom.url, base_download_dir) == expected_path

    # ... similar tests for other cases, such as playlists, other platforms, etc.


# And so on. Create more test functions to test other aspects of the class.
