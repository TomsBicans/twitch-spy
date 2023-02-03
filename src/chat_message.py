import os.path as path
from datetime import datetime
from src.util import OS
from src.util import bcolors
from src.util import mini_print
import re


class Message:
    """Object representing a chat message"""

    def __init__(self, log_entry: str) -> None:
        self.time_logged = self.get_time(log_entry)
        info = self.get_message_info(log_entry)
        self.username = info[0]
        self.channel = info[1]
        self.message = info[2]

    @staticmethod
    def get_time(log_entry: str):
        time_logged = log_entry.split()[0].strip()
        time_logged = datetime.strptime(time_logged, '%Y-%m-%d_%H:%M:%S')
        return time_logged

    @staticmethod
    def get_message_info(log_entry: str):
        """Get the username, channel and message text."""
        username_message = log_entry.split('—')[1:]
        username_message = '—'.join(username_message).strip()
        username, channel, message = re.search(
            ':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*?) :(.+)', username_message).groups()
        return (username, channel, message)

    def __str__(self) -> str:
        return f"{bcolors.WARNING}{str(self.time_logged)}{bcolors.ENDC} Channel: {bcolors.OKBLUE}{self.channel}{bcolors.ENDC} Username: {bcolors.FAIL}{self.username}{bcolors.ENDC} Message: {bcolors.OKGREEN}{self.message}{bcolors.ENDC}"


class MessageManager:
    def __init__(self, log_file: str) -> None:
        self.messages: list[Message] = self.extract_messages(log_file)

    @staticmethod
    def extract_messages(file: str):
        res = []
        content = OS.read_file(file)
        lines = content.split("\n")
        for line in lines:
            try:
                msg = Message(line)
                res.append(msg)
            except:
                pass
        return res

    def message_count(self):
        return len(self.messages)

    def word_count(self):
        res = 0
        for msg in self.messages:
            words = msg.message.split()
            res += len(words)
        return res

    def get_user_conversation(self, user: str, conversation=False):
        """Get every message that a user is involved in."""
        res = []
        others = self._find_replies(user)
        for msg in self.messages:
            if msg.username == user:
                res.append(msg)
            elif conversation and user in msg.message:
                res.append(msg)
            elif conversation and msg.username in others:
                res.append(msg)
        return res

    def _find_replies(self, user: str):
        """Find all people that a specific user has replied to"""
        all_users = self._get_all_users()
        res = []
        for msg in self.messages:
            if msg.username == user:
                other = re.search("@(\S+)", msg.message)
                if other is not None:
                    other = other.group(0)
                    other = other.replace("@", "")
                    if other in all_users:
                        res.append(other)
        return res

    def _get_all_users(self):
        """Get all users from chat log messages."""
        res = []
        for msg in self.messages:
            if msg.username not in res:
                res.append(msg.username)
        return res

    def get_word_frequency(self):
        """Calculate the number of individual word occurences."""
        res = {}
        for msg in self.messages:
            words = msg.message.split()
            for w in words:
                if res.get(w) is None:
                    res[w] = 1
                else:
                    res[w] += 1
        res = {k: v for k, v in reversed(
            sorted(res.items(), key=lambda item: item[1]))}
        return res

    def __str__(self):
        res = ""
        for msg in self.messages[-200:]:
            res += str(msg)+"\n"
        res += f"Message count: {self.message_count()}\n"
        res += f"Word count: {self.word_count()}\n"
        # res += f"Users: {str(self._get_all_users())}\n"
        res += f"Users: {str(mini_print(self._get_all_users(), threshold=500))}\n"
        res += f"User count: {len(self._get_all_users())}\n"
        return res


file_dir = path.dirname(__file__)
root_dir = path.join(file_dir, "dice", "data")
