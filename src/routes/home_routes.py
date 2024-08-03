from typing import List
from uuid import UUID
import psutil
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
from typing import TypedDict, List, Optional
import time

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


class CPUStats(TypedDict):
    usage: dict[str, float | List[float]]
    frequency: dict[str, float]
    temperature: dict[str, Optional[float]]
    loadAverage: dict[str, float]


class DiskStats(TypedDict):
    totalSpace: int
    usedSpace: int
    freeSpace: int
    usagePercentage: float
    readSpeed: int
    writeSpeed: int
    iops: int


class MemoryStats(TypedDict):
    total: int
    used: int
    free: int
    shared: int
    buffer: int
    available: int
    usagePercentage: float


class NetworkStats(TypedDict):
    interfaces: List[dict[str, str]]
    traffic: dict[str, int]
    bandwidth: dict[str, int]
    latency: float
    packetLoss: float


def get_cpu_stats() -> CPUStats:
    # Get CPU usage
    cpu_usage = psutil.cpu_percent(interval=1, percpu=True)

    # Get CPU frequency
    cpu_freq = psutil.cpu_freq()

    # Get CPU temperature (Note: This might not work on all systems)
    try:
        temp = psutil.sensors_temperatures()
        if "coretemp" in temp:
            current_temp = temp["coretemp"][0].current
            critical_temp = temp["coretemp"][0].critical
        else:
            current_temp = None
            critical_temp = None
    except AttributeError:
        current_temp = None
        critical_temp = None

    # Get load average
    load_avg = psutil.getloadavg()

    return {
        "usage": {"total": sum(cpu_usage) / len(cpu_usage), "perCore": cpu_usage},
        "frequency": {
            "current": cpu_freq.current * 1e6,  # Convert MHz to Hz
            "min": cpu_freq.min * 1e6,
            "max": cpu_freq.max * 1e6,
        },
        "temperature": {"current": current_temp, "critical": critical_temp},
        "loadAverage": {"1min": load_avg[0], "5min": load_avg[1], "15min": load_avg[2]},
    }


def get_memory_stats() -> MemoryStats:
    # Get memory usage
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "used": mem.used,
        "free": mem.free,
        "shared": mem.shared,
        "buffer": mem.buffers,
        "available": mem.available,
        "usagePercentage": mem.percent,
    }


def get_disk_stats() -> DiskStats:
    # Get disk usage
    disk = psutil.disk_usage("/")

    # Get disk I/O statistics
    disk_io = psutil.disk_io_counters()

    # Calculate read and write speeds (over 1 second interval)
    old_read = disk_io.read_bytes
    old_write = disk_io.write_bytes
    old_time = time.time()
    time.sleep(0.3)
    disk_io = psutil.disk_io_counters()
    new_read = disk_io.read_bytes
    new_write = disk_io.write_bytes
    new_time = time.time()

    read_speed = (new_read - old_read) / (new_time - old_time)
    write_speed = (new_write - old_write) / (new_time - old_time)

    # Calculate IOPS (I/O operations per second)
    old_iops = disk_io.read_count + disk_io.write_count
    new_iops = disk_io.read_count + disk_io.write_count
    iops = (new_iops - old_iops) / (new_time - old_time)

    return {
        "totalSpace": disk.total,
        "usedSpace": disk.used,
        "freeSpace": disk.free,
        "usagePercentage": disk.percent,
        "readSpeed": int(read_speed),
        "writeSpeed": int(write_speed),
        "iops": int(iops),
    }


def get_network_stats() -> NetworkStats:
    # Get network interfaces
    interfaces = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # IPv4
                interfaces.append({"name": interface, "ip": addr.address})
                break

    # Get network I/O statistics
    net_io = psutil.net_io_counters()

    # Calculate network traffic (over 1 second interval)
    old_sent = net_io.bytes_sent
    old_recv = net_io.bytes_recv
    old_time = time.time()
    time.sleep(0.3)
    net_io = psutil.net_io_counters()
    new_sent = net_io.bytes_sent
    new_recv = net_io.bytes_recv
    new_time = time.time()

    send_speed = (new_sent - old_sent) / (new_time - old_time)
    recv_speed = (new_recv - old_recv) / (new_time - old_time)

    # Note: Getting accurate latency and packet loss requires more complex measurements
    # These are placeholder values and should be replaced with actual measurements
    latency = 0.0
    packet_loss = 0.0

    return {
        "interfaces": interfaces,
        "traffic": {"sent": int(new_sent), "received": int(new_recv)},
        "bandwidth": {"upload": int(send_speed), "download": int(recv_speed)},
        "latency": latency,
        "packetLoss": packet_loss,
    }


@home_routes.route("/system_stats_CPU", methods=["GET"])
def get_system_stats_CPU():
    logger.debug("Fetching CPU stats.")
    cpu_stats = get_cpu_stats()
    return jsonify(cpu_stats)


@home_routes.route("/system_stats_ALL", methods=["GET"])
def get_system_stats_ALL():
    logger.debug("Fetching system stats.")
    cpu_stats = get_cpu_stats()
    mem_stats = get_memory_stats()
    disk_stats = get_disk_stats()
    network_stats = get_network_stats()
    return jsonify(
        {
            "cpu": cpu_stats,
            "memory": mem_stats,
            "disk": disk_stats,
            "network": network_stats,
        }
    )
