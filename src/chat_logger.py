from datetime import datetime
import config
from chat_message import Message
from util import OS, bcolors
import socket
import logging
from emoji import demojize
import atexit
from multiprocessing import Process
import sys
import argparse
import time
import os.path as path


class Chat_logger:
    """more info: https://www.learndatasci.com/tutorials/how-stream-text-data-twitch-sockets-python/"""

    def __init__(self, channel: str) -> None:
        self.server = 'irc.chat.twitch.tv'
        self.port = 6667
        self.nickname = 'Feagleyy'
        self.token = 'oauth:ubyeyu7pbrfpf3dha63eg1hwmmx55d'
        self.channel = "#" + channel
        self.socket = None
        self.log_name = f'{self.get_channel()}_chat.log'
        self.process: Process = Process()
        atexit.register(self.__del__)

    def auth_socket(self):
        print(f"Authorizing a new socket at: {self.server}:{self.port}")
        sock = socket.socket()
        sock.connect((self.server, self.port))
        sock.send(f"PASS {self.token}\n".encode('utf-8'))
        sock.send(f"NICK {self.nickname}\n".encode('utf-8'))
        sock.send(f"JOIN {self.channel}\n".encode('utf-8'))
        return sock

    def get_channel(self):
        chnl = self.channel.replace("#", "")
        return chnl

    def get_log_file(self):
        """Return the absolute location of the log file."""
        # datetime.strftime(datetime.now(), )
        OS.create_dir(config.CHAT_LOGS)
        return path.join(config.CHAT_LOGS, self.log_name)

    def setup_logger(self):
        print(f"Setting up logger. Loggin chat at: {self.get_log_file()}")
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s — %(message)s',
                            datefmt='%Y-%m-%d_%H:%M:%S',
                            handlers=[logging.FileHandler(self.get_log_file(), encoding='utf-8')])

    def start_logging(self):
        self.setup_logger()
        try:
            try:
                while True:
                    resp = self.socket.recv(2048).decode('utf-8')
                    if resp.startswith('PING'):
                        self.socket.send("PONG\n".encode('utf-8'))

                    elif len(resp) > 0:
                        logging.info(demojize(resp))
            except Exception as e:
                print(f"{bcolors.FAIL}{e}{bcolors.ENDC}")
                sys.exit(1)
        except KeyboardInterrupt:
            print("Interupted.")

    def start_process(self):
        if not self.process.is_alive():
            self.socket = self.auth_socket()
            p = Process(target=self.start_logging)
            p.name = self.channel
            self.process = p
            self.process.start()
            time.sleep(0.05)
        else:
            print(f"{self.process} is alive.")

    def __del__(self):
        print(f"Closing socket: {self.socket}")
        self.socket.close()
        if self.process.is_alive():
            print(f"Terminating logging process: {self.process}")
            try:
                self.process.terminate()
            except Exception as e:
                print(f"{bcolors.FAIL}{e}{bcolors.ENDC}")
        time.sleep(0.05)

    def __str__(self) -> str:
        res = ""
        alive = self.process.is_alive()
        if alive:
            res += f"{bcolors.OKGREEN}{self.process}{bcolors.ENDC} : {self.process.is_alive()}. log: {bcolors.OKBLUE}{self.get_log_file()}{bcolors.ENDC}\n"
        else:
            res += f"{bcolors.FAIL}{self.process}{bcolors.ENDC} : {self.process.is_alive()}. log: {bcolors.OKBLUE}{self.get_log_file()}{bcolors.ENDC}\n"
        return res


class ChatMultiLogger:
    def __init__(self) -> None:
        self.loggers: list[Chat_logger] = []

    def add_logger(self, channel: str):
        listener = Chat_logger(channel)
        self.loggers.append(listener)

    def start_loggers(self):
        """Activate all loggers. Activate only if not running already."""
        for log in self.loggers:
            if not log.process.is_alive():
                log.start_process()

    def disable_loggers(self):
        for log in self.loggers:
            if log.process.is_alive():
                print(f"Terminating: {log}")
                log.__del__()

    def __str__(self) -> str:
        res = ""
        for log in self.loggers:
            res += str(log)
        return res


def is_favourite_channel(args):
    """Check if favourite channels need to be logged."""
    for item in args:
        item = str(item)
        if item.lower() == "fav":
            return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi twitch chat logger.")
    parser.add_argument('channels', metavar="chan", type=str, nargs="+",
                        help="Channels you want to log the chat. Put 'fav' if you want to activate loggers for all favorite channels")
    args = parser.parse_args()

    logging.basicConfig(filename='program.log',
                        level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    favourite_channels = [
        "raw_lv",
        "mikerics",
        # "skima_",
        "sidratons",
        "imkompots",
        "speletlvgaming",
        "annnn4",
        "hyskeee",
        "keen_csgo1",
        "vadikus007",
        "ayrrix",
        "kleverrlv",
        # "thageneral_r2",
        # "popazik",
        # "scvodarchives",
        # "field9",
        # "melina",
        # "nanajam777",
        # "39daph",
        # "prelidencs",
        # "cohhcarnage",
        # "sodapoppin",
        "root_supernova",
        # "trainwreckstv",
        # "kntent",
        # "rineksa",
        # "semmler",
        # "esl_sc2",
        "forsen",
        "thageneral_r2",
    ]
    chat_manager = ChatMultiLogger()
    if is_favourite_channel(args.channels):
        print("Logging favourite channels.")
        for channel in favourite_channels:
            channel = str(channel)
            chat_manager.add_logger(channel)
    else:
        for channel in args.channels:
            channel = str(channel)
            chat_manager.add_logger(channel)

    try:
        chat_manager.start_loggers()
        while True:
            logging.info(str(datetime.now()))
            logging.info(str(chat_manager))
            print(str(datetime.now()))
            print(chat_manager)
            chat_manager.start_loggers()
            time.sleep(20)
    except KeyboardInterrupt:
        chat_manager.disable_loggers()
        print(chat_manager)
