from flask import Blueprint, render_template, jsonify
import src.app as app
import src.util as util
import flask

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
            # cli_thread = threading.Thread(target=my_app.main_cli, args=(urls_list,))
            # cli_thread.start()
            print(urls_list)
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
