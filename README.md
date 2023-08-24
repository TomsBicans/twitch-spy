# yt-dlp-music

# Description
This is a project that aims to create an easy to use music downloading and library management software that can be run locally on a computer. It has ambitions to work with various audio and video content webstites, but currently it supports music download feature from youtube.com.
The core feature is audio downloading from youtube, metadata and thumbnail asignment and downloaded library content management. The system comes with an easy to overlook UI with realtime updates.

This project makes it easy and straightforward to download and manage an audio library on a computer.

# Features
**yt-dlp as backend technology**: The main component to communicate with external services is the yt-dlp open source library (https://github.com/yt-dlp/yt-dlp)

**Atomization**: The user can provide any input (single video, playlist or channel) and the program will try to figure it out how to create a list of smallest entities possible from this input (in this case, a list of videos). Each of the entity is being treated as a separate job (atom) and can be processed in parallel with other jobs.

**Multithreading**: Utilizes python's threadpoolexecutor to process multiple jobs at once, thus maximizing the speed of job processing, since each job is network I/O bound.

**Realtime UI updates**: UI is developed using event-driven programming paradigm for sending status updates using a local socket connection. This creates a very responsive website that accurately represents the internal state of the system.



# View the progress of development here:
https://trello.com/b/0DEbMAds/development-board



# Installation:
1. Install python3 (https://www.python.org/downloads/)
2. Clone this project's repository. (https://github.com/TomsBicans/twitch-spy)
3. Install project dependencies.
On windows:
```
install-dev-windows.bat
```
On linux:
```
install-dev-linux.sh
```
4. Run the program.

# Run the program:
This will launch a local python flask server. 
```
py ./main.py
```
or
```
python3 ./main.py
```
It is dependant on the system name used to launch python3.



In the terminal you can see the IP to which you have to connect to access the frontend interface. It will most likely be this IP:
```
http://127.0.0.1:5000/
```

# Usage
1. Launch the local server (py ./main.py)
2. Connect to the local server instance IP address. (http://127.0.0.1:5000/)
3. Paste in the links you want for the system to process and download.
4. See realtime updates on the jobs being processed.
5. Enjoy your music!
