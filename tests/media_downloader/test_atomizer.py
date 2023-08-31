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


def test_is_url_valid():
    assert atomizer.Atom._is_url_valid("https://youtube.com/watch?v=someID") == True
    assert atomizer.Atom._is_url_valid("http://youtube.com/watch?v=someID") == True
    assert atomizer.Atom._is_url_valid("youtube.com/watch?v=someID") == False
    assert atomizer.Atom._is_url_valid("htttp://invalidurl.com") == False
    assert atomizer.Atom._is_url_valid("") == False
    assert atomizer.Atom._is_url_valid(None) == False


def test_atom_initialization():
    atom = atomizer.Atom(
        "https://youtube.com/watch?v=someID",
        const.CONTENT_MODE.AUDIO,
        "/path/to/download",
    )

    assert atom.url == "https://youtube.com/watch?v=someID"
    assert atom.content_type == const.CONTENT_MODE.AUDIO
    assert atom.download_dir == "/path/to/download"
    assert atom.status == const.PROCESS_STATUS.QUEUED


def test_atomize_urls():
    urls = [
        "https://youtube.com/watch?v=someID",
        "https://twitch.tv/somechannel",
        "https://someotherwebsite.com/",
    ]

    atoms = atomizer.Atomizer.atomize_urls(
        urls, const.CONTENT_MODE.AUDIO, "/path/to/download"
    )

    assert len(atoms) == 3  # Ensure we get 3 atoms

    youtube_atoms = [atom for atom in atoms if atom.platform == const.PLATFORM.YOUTUBE]
    twitch_atoms = [atom for atom in atoms if atom.platform == const.PLATFORM.TWITCH]
    undefined_atoms = [
        atom for atom in atoms if atom.platform == const.PLATFORM.UNDEFINED
    ]

    assert len(youtube_atoms) == 1
    assert len(twitch_atoms) == 1
    assert len(undefined_atoms) == 1


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
