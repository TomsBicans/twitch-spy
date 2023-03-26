import requests


def is_channel_live(channel_name: str):
    url = f'https://api.twitch.tv/kraken/streams/{channel_name}'
    headers = {
        'Client-ID': '47wjywdm3kyes0ko263s5ui7g9xz37',  # replace with your Twitch API client ID
        'Accept': 'application/vnd.twitchtv.v5+json'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    if data['stream'] is not None:
        return True
    else:
        return False
