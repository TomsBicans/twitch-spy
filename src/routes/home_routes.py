from flask import Blueprint, render_template, jsonify
import config
import src.app as app
import src.util as util
import src.media_downloader.atomizer as atomizer
import src.media_downloader.constants as const
import flask
import os.path as path

home_routes = Blueprint("home_routes", __name__)


@home_routes.route("/test")
def home():
    return render_template("home.html")


@home_routes.route("/", methods=["GET", "POST"])
def get_queue():
    # Get the MyApp instance from the Flask app's configuration
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]

    if flask.request.method == "POST":
        urls = flask.request.form.get("urls")
        if urls:
            urls_list = [url.strip() for url in urls.split("\n")]
            jobs = atomizer.Atomizer.atomize_urls(
                urls_list,
                const.CONTENT_MODE.AUDIO,
                path.join(config.STREAM_DOWNLOADS, "audio_library"),
            )
            [print(job) for job in jobs]
            print(len(jobs))
            return flask.redirect(
                flask.url_for("home_routes.get_queue")
            )  # Redirect to the same page to show updated status

    # Get the state of the queues
    audio_in = [s.strip() for s in my_app.audio_manager.file_queue.input_file.read()]
    audio_ongoing = [
        s.strip() for s in my_app.audio_manager.file_queue.ongoing_file.read()
    ]
    audio_finished = [
        s.strip() for s in my_app.audio_manager.file_queue.finished_file.read()
    ]

    video_in = [s.strip() for s in my_app.video_manager.file_queue.input_file.read()]
    video_ongoing = [
        s.strip() for s in my_app.video_manager.file_queue.ongoing_file.read()
    ]
    video_finished = [
        s.strip() for s in my_app.video_manager.file_queue.finished_file.read()
    ]

    return render_template(
        "home.html",
        audio_in=audio_in,
        audio_ongoing=audio_ongoing,
        audio_finished=audio_finished,
        video_in=video_in,
        video_ongoing=video_ongoing,
        video_finished=video_finished,
    )
