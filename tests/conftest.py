import tempfile

from twitch_spy import config


config.init(tempfile.mkdtemp(prefix="twitch-spy-tests-"))
