from src.video_downloader.twitch import TwitchDownloader
from src.twitch_api import api_client
import config

if __name__ == "__main__":
    downloader = TwitchDownloader()
    downloader.download_stream("https://www.twitch.tv/rawchixx", config.STREAM_DOWNLOADS)
    # # channel_url = "https://www.twitch.tv/rawchixx"
    # channel_name = "rawchixx"
    # is_live = api_client.is_channel_live(channel_name)
    # print(is_live)
