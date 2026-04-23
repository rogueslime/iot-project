import sounddevice as sd
from scipy.io.wavfile import write
import librosa
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean, cosine
import os
import time

## Cryptography + additional imports, TB
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import requests
import base64
import pickle

## Generate client side key, TB
client_private_key = ec.generate_private_key(ec.SECP256R1())
client_public_key = client_private_key.public_key()
private_bytes = client_private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())

def get_client_public_bytes():
    return client_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

# Get public key from server, TB
def get_server_public_key():
    res = requests.get("http://localhost:8000/public-key")
    return res.json()["public_key"].encode()

# Shared key derivation, TB
def derive_shared_key(server_pub_bytes):
    server_pub = serialization.load_pem_public_key(server_pub_bytes)

    shared = client_private_key.exchange(ec.ECDH(), server_pub)

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'iot-auth'
    ).derive(shared)

# MFCC encryption,, TB
def encrypt_mfcc(mfcc, key):
    data = pickle.dumps(mfcc)

    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    encryptor = cipher.encryptor()

    ciphertext = encryptor.update(data) + encryptor.finalize()

    return iv, ciphertext

# Send MFCCs to server for validation, TB
def send_to_server(username, mfcc):
    # Step 1: get server public key
    server_pub = get_server_public_key()

    # Step 2: derive shared key
    key = derive_shared_key(server_pub)

    # Step 3: encrypt MFCC
    iv, ciphertext = encrypt_mfcc(mfcc, key)

    payload = {
        "user_id": username,
        "client_pub_key": get_client_public_bytes().decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }

    res = requests.post("http://localhost:8000/authenticate", json=payload)

    return res.json()

# Ensure MFCC shape fits definition
TARGET_MFCC = 20
TARGET_FRAMES = 216

"""def fix_mfcc_shape(mfcc):
    if mfcc.shape[0] > TARGET_MFCC:
        mfcc = mfcc[:TARGET_MFCC, :]
    elif mfcc.shape[0] < TARGET_MFCC:
        pad = TARGET_MFCC - mfcc.shape[0]
        mfcc = np.pad(mfcc, ((0, pad), (0, 0)), mode='reflect')

    if mfcc.shape[1] > TARGET_FRAMES:
        mfcc = mfcc[:, :TARGET_FRAMES]
    elif mfcc.shape[1] < TARGET_FRAMES:
        pad = TARGET_FRAMES - mfcc.shape[1]
        mfcc = np.pad(mfcc, ((0, 0), (0, pad)), mode='constant')

    return mfcc
"""

# Print client keypair
print("\nCLIENT KEYS:")
print("\nClient Public Key: ",get_client_public_bytes().decode())
print("\nClient Private Key: ", private_bytes)
# Print server public key
print("\nSERVER PUBLIC KEY:")
server_pub = get_server_public_key()
print("\n",server_pub.decode())
# Print shared key
print("\nCLIENT DERIVED SHARED KEY:")
key = derive_shared_key(server_pub)
print("\n",key.hex())

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


"""
def newUser():
	username = input("Enter a username")
	filepath = os.path.join("users", f"{username}.wav")
	if os.path.exists(filepath):
		print("User already exists")
		return False, username

	record(username)
	os.rename(f"{username}.wav",filepath)
	return True, username
"""

## Create new user in server instead, TB
def newUser():
    username = input("Enter a username")

    mfcc = record(username)

    response = send_to_server(username, mfcc)

    print("Server response:", response)

    return True, username

"""
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
"""
## Server authentication, TB
def authenticate():
    username = input("Enter your username")

    mfcc_recording = record(username)

    response = send_to_server(username, mfcc_recording)

    print("Server response:", response)

    if response.get("status") == "authenticated":
        return True, username
    elif response.get("status") == "enrolled":
        print("User enrolled on server")
        return True, username
    else:
        return False, username

def record(username):
	print("This is a 5 second recording")
	print("When you are ready to start, press enter")
	print("Speak your password")
	val = input()
	## this sleep is important, do not remove it. Otherwise the program will just record your keyboard
	time.sleep(0.5)
	print("recording")
	recording = sd.rec(
    	int(duration * samplerate),
    	samplerate=samplerate,
    	channels=2,
    	dtype='float32'
	)
	sd.wait()
	output = f"{username}.wav"
	write(output, samplerate, recording)
	print("Recording finished.")
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
	"""
      
	mfccs = librosa.feature.mfcc(
	    y=y,
    	sr=sr,
    	n_mfcc=20   # directly get 20
	)
	# Normalize (keep this)
	mfccs = mfccs - np.mean(mfccs, axis=1, keepdims=True)
	# Fix shape
	mfccs = fix_mfcc_shape(mfccs)
	"""
	print("MFCC shape:", mfccs.shape)  # should ALWAYS be (19, x) with x being 216 or less
	
	return mfccs

# Secure message send
def send_secure_message(sender, recipient, message):
    server_pub = get_server_public_key()

    key = derive_shared_key(server_pub)

    payload_data = {
        "sender": sender,
        "recipient": recipient,
        "message": message
    }

    data_bytes = pickle.dumps(payload_data)

    # Step 4: encrypt
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data_bytes) + encryptor.finalize()
    print("Message before encryption: ", message,"\n")
    print("Encrypted message: ", ciphertext,"\n")

    payload = {
        "sender_id": sender,
        "recipient_id": recipient,
        "client_pub_key": get_client_public_bytes().decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }

    res = requests.post("http://localhost:8000/send-message", json=payload)

    return res.json()

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
		recipient = input("Enter recipient username: ")
		message = input("Enter message: ")
		response = send_secure_message(user, recipient, message)
		print("Server response:", response)
	else:
		print("Begone foul demon")


if __name__ == "__main__":
	main()
