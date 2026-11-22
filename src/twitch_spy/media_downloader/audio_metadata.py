import logging

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError


logger = logging.getLogger(__name__)


def read_mp3_artist(file_path: str) -> str | None:
    try:
        artists = EasyID3(file_path).get("artist", [])
    except ID3NoHeaderError:
        return None
    except (OSError, MutagenError) as error:
        logger.warning("Could not read artist from %s: %s", file_path, error)
        return None

    return ", ".join(artist.strip() for artist in artists if artist.strip()) or None
