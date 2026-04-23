To run this project perform the following steps:
Steps will vary for each OS and CLI.
1. run git clone https://github.com/rogueslime/iot-project
2. if you do not have docker installed, you will need: docker, docker-compose, and buildx
3. cd into the directory and run docker-compose build (may need to run as administrator or with sudo on linux)
4. run docker-compose up to start the server. You can attach the -d tag to run it detached to only use one terminal page.
5. run python -m venv .venv
6. run source venv/bin/activate
7. pip install the python packages: librosa, cryptography, sounddevice, and fastdtw.
8. run python audiorepo.py and follow the cli instructions.
     -- you will need to create a user then run the program again as current user to  authenticate as that user--
