from flask import Blueprint, render_template, jsonify
import config
import src.app as app
import src.util as util
import src.media_downloader.atomizer as atomizer
import src.media_downloader.constants as const
import flask
import os.path as path
from src.socket_instance import socketio

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
            for job in jobs:
                my_app.event_dispatcher.dispatch_event("job_created", job)
                my_app.job_manager.add_job(job)

            return jsonify({"success": True})
    return render_template("home.html")


@socketio.on("request_initial_data")
def handle_ready_for_data():
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]
    for job in my_app.job_manager.get_all_jobs():
        my_app.event_dispatcher.dispatch_event("job_render", job)
