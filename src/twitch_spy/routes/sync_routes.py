"""
Flask routes for Android sync.

Endpoints
---------
GET  /sync/devices   — check whether a device is connected via adb
POST /sync/plan      — compute transfer operations without touching the device
POST /sync/execute   — run a plan in a background thread; emits Socket.IO events
                       for progress and completion

Socket.IO events emitted during execute
----------------------------------------
  sync_progress  { current, total, filename, remote_path, status }
  sync_complete  { uploaded, skipped, failed, errors }
"""

import threading

import flask
from flask import Blueprint, jsonify, request

import twitch_spy.config as config
import twitch_spy.util as util
from twitch_spy.android_sync.adb_sync import (
    AndroidLibrarySync,
    FileTransferOp,
    SyncPlan,
)
from twitch_spy.socket_instance import socketio
from twitch_spy.system_logger import logger

sync_routes = Blueprint("sync_routes", __name__)


def _syncer() -> AndroidLibrarySync:
    return AndroidLibrarySync(
        adb_exe="adb.exe",
        android_dest=config.ANDROID_DEST,
    )


@sync_routes.route("/sync/devices", methods=["GET"])
def get_devices():
    """List connected adb devices and report whether any are online."""
    syncer = _syncer()
    devices = syncer.list_devices()
    return jsonify({"devices": devices, "connected": len(devices) > 0})


@sync_routes.route("/sync/plan", methods=["POST"])
def plan_sync():
    """
    Compute the set of files that need to be transferred.

    Reads the remote device once (bulk find) and walks the local audio library.
    Returns a SyncPlan JSON object that the client holds and sends back on confirm.

    No files are written to the device.
    """
    syncer = _syncer()

    if not syncer.device_connected():
        return jsonify({"error": "No Android device connected via adb"}), 503

    try:
        plan = syncer.plan_sync(config.AUDIO_LIBRARY)
        return jsonify(plan.to_dict())
    except Exception as exc:
        logger.error("plan_sync error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@sync_routes.route("/sync/execute", methods=["POST"])
def execute_sync():
    """
    Accept a SyncPlan (JSON body from /sync/plan) and execute it.

    Returns 202 immediately.  Progress is streamed via Socket.IO:
      - sync_progress  { current, total, filename, remote_path, status }
      - sync_complete  { uploaded, skipped, failed, errors }

    The plan is re-validated on the server so the client cannot inject
    arbitrary paths.
    """
    data = request.json or {}

    try:
        plan = SyncPlan(
            dirs_to_create=list(data["dirs_to_create"]),
            files_to_transfer=[
                FileTransferOp(**op) for op in data["files_to_transfer"]
            ],
            skipped_count=int(data["skipped_count"]),
            total_transfer_bytes=int(data["total_transfer_bytes"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid plan payload: {exc}"}), 400

    syncer = _syncer()

    def run() -> None:
        def on_progress(
            current: int, total: int, op: FileTransferOp, status: str
        ) -> None:
            socketio.emit(
                "sync_progress",
                {
                    "current": current,
                    "total": total,
                    "filename": op.filename,
                    "remote_path": op.remote_path,
                    "status": status,
                },
            )

        result = syncer.execute_plan(plan, progress_callback=on_progress)
        socketio.emit("sync_complete", result.to_dict())

    thread = threading.Thread(target=run, daemon=True, name="android-sync")
    thread.start()

    return jsonify({"message": "Sync started"}), 202
