# twitch-spy

# Description
main.py is the primary entry point for the Twitch Spy program. This script initiates the video download process from different platforms. The main feature currently is audio downloading from youtube, metadata asignment and downloaded library content management.

# Features
Multithreading: Utilizes multiple worker threads for concurrent downloading. The number of threads can be configured using the --num-worker-threads option.

File Queue: Handles a queue of URLs from which to download videos. The script can be configured to continuously listen to this file queue using the --file-queue-mode option.

User Input: Manages user input, allowing the addition of new video URLs while the program is running.

Performance: Tracks the time taken by the program to complete its tasks and prints it to the console at the end.




# Installation:
1. Install python3
2. Clone this repository.

On windows:
```
python3 -m venv venv
venv/Scripts/Activate.ps1
python3 -m pip install -r requirements.txt
python3 .\main.py -h
```
or 
```
py -m venv venv
venv/Scripts/Activate.ps1
py -m pip install -r requirements.txt
py .\main.py -h
```
Paste the url you want to process in the terminal or launch program with the url's as arguments.
On linux:
```
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py -h
```
# Usage
1. Paste the URL you want to process in the terminal. The program listens for input in the standard user input stream.
2. Alternatively, you can launch the program with the URLs as arguments.
3. Alternatively, if you use file queue mode. There will be a text file generated on the OS. The program continously scans and feeds the data found in the input file to the runtime program. The program also keeps track of the active jobs it is working on, so it is possible to terminate the program, start it again and it will continue where it left off.
