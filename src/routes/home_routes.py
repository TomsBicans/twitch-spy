from flask import Blueprint, render_template, jsonify
import config
import src.app as app
import src.util as util
import src.media_downloader.platform_handlers as ph
import src.media_downloader.constants as const
import src.media_downloader.storage_manager as sm
from src.event_dispatcher import Events
import flask
import os.path as path
from src.socket_instance import socketio
from src.system_logger import logger
from src.media_downloader.constants import lock

home_routes = Blueprint("home_routes", __name__)


@home_routes.route("/test")
def home():
    return render_template("home.html")


@home_routes.route("/", methods=["GET", "POST"])
def get_queue():
    logger.debug("Handling root route.")
    # Get the MyApp instance from the Flask app's configuration
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]

    if flask.request.method == "POST":
        logger.debug("POST method detected")
        urls = flask.request.form.get("urls")
        if urls:
            urls_list = [url.strip() for url in urls.split("\n")]
            logger.debug(f"URLs list: {urls_list}")
            user_input = sm.StorageManager(config.STREAM_DOWNLOADS)
            with lock:
                for url in urls_list:
                    user_input.mark_successful_download(url)
            jobs = ph.Atomizer.atomize_urls(
                urls_list,
                const.CONTENT_MODE.AUDIO,
                config.AUDIO_LIBRARY,
            )
            logger.debug(f"Jobs created: {jobs}")
            logger.debug(f"Number of jobs: {len(jobs)}")
            for job in jobs:
                my_app.job_manager.add_job(job)
                my_app.event_dispatcher.dispatch_event(Events.JOB_CREATED.value, job)
                my_app.event_dispatcher.dispatch_event(
                    Events.STATISTICS_UPDATE.value, my_app.job_manager.stats
                )

            return jsonify({"success": True})
    return render_template("home.html")


@socketio.on("request_initial_data")
def handle_ready_for_data():
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]
    my_app.event_dispatcher.dispatch_event(
        Events.STATISTICS_UPDATE.value, my_app.job_manager.stats
    )
    for job in my_app.job_manager.get_all_jobs():
        my_app.event_dispatcher.dispatch_event(Events.JOB_RENDER.value, job)
