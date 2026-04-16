import sounddevice as sd
from scipy.io.wavfile import write
import librosa
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean, cosine
import os
import time

## This checks for a users directory and makes it if it doesnt exist
os.makedirs("users", exist_ok=True)

## a couple approaches we could take are sounddevice for code simplicity
## or we can do pyaudio for more control. For ease of design I will implement
## sounddevice and we can swap to pyaudio if needed.

sd.default.samplerate = 44100 ## This is the sample rate. 44.1 kHz is the industry standard. 
samplerate = sd.default.samplerate
sd.default.channels = 2
######## do not use this line on your device. run python -m sounddevice to know which device id you want to use
##sd.default.device = 9
##############################
duration = 5  ## seconds of recording time.



def newUser():
	username = input("Enter a username")
	filepath = os.path.join("users", f"{username}.wav")
	if os.path.exists(filepath):
		print("User already exists")
		return False, username

	record(username)
	os.rename(f"{username}.wav",filepath)
	return True, username

def authenticate():
	username = input("Enter your username")
	## grab file here from users folder and check if it exists
	
	filepath = os.path.join("users", f"{username}.wav")
	## Checks for if there is a saved audio file for the user first
	if not os.path.exists(filepath):
		print("User does not exist")
		return False, username
		
	y, sr = librosa.load(filepath)
	y, index = librosa.effects.trim(y, top_db=20)
	mfcc_user = librosa.feature.mfcc(y=y, sr=sr)
	mfcc_user = mfcc_user[1:, :]
		
	mfcc_user = mfcc_user - np.mean(mfcc_user, axis=1, keepdims=True)
	## transposing the mfccs to use with fastdtw\
	mfcc_recording = record(username)
	mfcc_userDTW = mfcc_user.T
	mfcc_recordingDTW = mfcc_recording.T
	
	distance, path = fastdtw(mfcc_recordingDTW, mfcc_userDTW, dist=cosine)
	## adjust threshold to make the comparison more or less strict
	Threshold = 0.3
	distance = distance / len(path)
	
	## printing the distance to get a general idea of the distance
	print(distance)
	if distance < Threshold:
		authorized = True
	else:
		authorized = False
		
	return authorized, username

def record(username):
	print("This is a 5 second recording")
	print("When you are ready to start, press enter")
	print("Speak your password")
	val = input()
	## this sleep is important, do not remove it. Otherwise the program will just record your keyboard
	time.sleep(0.5)
	print("recording")
	recording = sd.rec(int(duration * samplerate))
	sd.wait()
	output = f"{username}.wav"
	write(output, samplerate, recording)

	y, sr = librosa.load(output)
	
	## This is another potential point of failure. The trimming may need to
	## have the top_db changed to fit the noise level of the room
	## decrease the db if you have more background noise
	## increase the db for silent environements
	y , index = librosa.effects.trim(y, top_db=20)
	
	## This is for debugging the trim 
	print(librosa.get_duration(y=y, sr=sr))
	
	mfccs = librosa.feature.mfcc(y=y, sr=sr)
	
	## This drops the volume coefficient of the mfcc
	mfccs = mfccs[1:, :]
	
	mfccs = mfccs - np.mean(mfccs, axis=1, keepdims=True)

	return mfccs



def main():
	print("Please select an option")
	print()
	print("1. Current user")
	print("2. New user")
	print("3. Exit")

	val = int(input())
	match val:
		case 1:
			authorized, user = authenticate()
		case 2:
			authorized, user = newUser()
		case 3:
			exit()
		case _:
			print("Invalid input")
			return
	if authorized:
		print(f"Welcome {user}")
		print()
		message = input("Enter a message to send")
		print("Add ECC and Send the message over here")
	else:
		print("Begone foul demon")


if __name__ == "__main__":
	main()
