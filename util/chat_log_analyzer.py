import sys
import os
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
from src.chat_message import Message
from src.chat_message import MessageManager
from src.chat_logger import Chat_logger
from util.file import File
from datetime import datetime
# set PYTHONPATH="${PYTHONPATH}:C:\Users\feagl\Documents\GIT_REPOS\twitch-spy"

if __name__ == "__main__":
    file = sys.argv[1]
    try:
        user = sys.argv[2]
    except:
        user = None

    try:
        conversation = sys.argv[3]
    except:
        conversation = False
    pre = datetime.now()
    msg_manager = MessageManager(file)
    print(msg_manager)
    if user is not None:
        user_msg = msg_manager.get_user_conversation(user, conversation=bool(conversation))
        for msg in user_msg:
            print(msg)

    after = datetime.now()
    print(f"Processing time: {after - pre}")

    # words = msg_manager.get_word_frequency()
    # for k,v in words.items():
    #     if v >= 1:
    #         print(k, ":", v)