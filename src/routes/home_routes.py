from typing import List
from uuid import UUID
from flask import Blueprint, render_template, jsonify
import config
import src.app as app
from src.media_downloader.atomizer import Atom
import src.util as util
import src.media_downloader.platform_handlers as ph
import src.media_downloader.constants as const
import src.media_downloader.storage_manager as sm
from src.event_dispatcher import Events
import flask
import os.path as path
from src.socket_instance import socketio
from src.system_logger import logger

home_routes = Blueprint("home_routes", __name__)


@home_routes.route("/form_submit", methods=["POST"])
def form_submit():
    logger.debug("Handling form submit.")
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]

    logger.debug("POST method detected")
    data = flask.request.json
    urls = data.get("urls")
    logger.debug(f"URLs: {urls}")
    if urls:
        urls_list = [url.strip() for url in urls.split("\n")]
        logger.debug(f"URLs list: {urls_list}")
        user_input = sm.StorageManager(config.STREAM_DOWNLOADS)
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

    return jsonify({"success": False})


@socketio.on("request_initial_data")
def handle_ready_for_data():
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]
    my_app.event_dispatcher.dispatch_event(
        Events.STATISTICS_UPDATE.value, my_app.job_manager.stats
    )
    for job in my_app.job_manager.get_all_jobs():
        my_app.event_dispatcher.dispatch_event(Events.JOB_RENDER.value, job)


@home_routes.route("/jobs", methods=["GET"])
def get_all_jobs():
    logger.debug("Fetching all jobs.")
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]
    all_jobs: List[Atom] = my_app.job_manager.get_all_jobs()
    jobs_list = [job.to_dict() for job in all_jobs]
    return jsonify(jobs_list)


@home_routes.route("/jobs/<job_id>", methods=["GET"])
def get_job_by_id(job_id):
    logger.debug(f"Fetching job: {job_id}")
    my_app: app.Application = flask.current_app.config[util.MagicStrings.APP]
    job = my_app.job_manager.get_job(UUID(job_id))
    if job:
        return jsonify(job.to_dict())
    else:
        return jsonify({"error": "Job not found"}), 404
