import youtube


def test_youtube_playlist_videos():
    playlist = (
        "https://www.youtube.com/playlist?list=PLCgSXQYoBb41x3JaoF9vlpQ7Yo9oIHqqN"
    )
    videos = youtube.get_playlist_video_urls(playlist)
    print(videos)


def test_youtube_playlist_videos2():
    playlist = "https://www.youtube.com/playlist?app=desktop&list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj"
    videos = youtube.get_playlist_video_urls(playlist)
    print(videos)


def test_youtube_playlist_title():
    playlist = (
        "https://www.youtube.com/playlist?list=PLCgSXQYoBb41x3JaoF9vlpQ7Yo9oIHqqN"
    )
    title = youtube.get_playlist_name(playlist)
    print(title)


test_youtube_playlist_videos()
test_youtube_playlist_videos2()
test_youtube_playlist_title()
