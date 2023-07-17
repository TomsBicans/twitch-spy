from flask import Blueprint, render_template, jsonify
import src.app as app
import flask

home_routes = Blueprint("home_routes", __name__)


@home_routes.route("/")
def home():
    return render_template("home.html")


@home_routes.route("/queue", methods=["GET"])
def get_queue():
    # Get the MyApp instance from the Flask app's configuration
    my_app: app.Application = flask.current_app.config["my_app"]

    # Get the state of the queues
    audio_state = my_app.audio_file_queue.read_from_input()
    video_state = my_app.video_file_queue.read_from_input()

    # Return the state of the queues as a JSON response
    return jsonify(
        {
            "audio": audio_state,
            "video": video_state,
        }
    )
