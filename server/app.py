from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import os
import base64
import pickle
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from crypto_utils import derive_key, decrypt, get_public_key_bytes

app = FastAPI()

# Check for data directory
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

class AuthRequest(BaseModel):
    user_id: str
    client_pub_key: str
    iv: str
    ciphertext: str

class MessageRequest(BaseModel):
    sender_id: str
    recipient_id: str
    client_pub_key: str
    iv: str
    ciphertext: str

# Calculate distance of MFCCs
def compare_mfcc(mfcc1, mfcc2):
    print("dtype mfcc1:", mfcc1.dtype)
    print("dtype mfcc2:", mfcc2.dtype)

    print("shape mfcc1:", mfcc1.shape)
    print("shape mfcc2:", mfcc2.shape)

    print("nan mfcc1:", np.isnan(mfcc1).any())
    print("nan mfcc2:", np.isnan(mfcc2).any())

    mfcc1 = mfcc1.T
    mfcc2 = mfcc2.T

    distance, _ = fastdtw(mfcc1, mfcc2, dist=euclidean)

    return distance / len(mfcc1)

@app.get("/")
def root():
    return {"message": "IoT Auth Server Running"}

@app.get("/public-key")
def public_key():
    return {"public_key": get_public_key_bytes().decode()}

@app.post("/authenticate")
def authenticate(req: AuthRequest):
    # Derive key
    key = derive_key(req.client_pub_key.encode())

    # Decode inputs from text into bytes
    iv = base64.b64decode(req.iv)
    ciphertext = base64.b64decode(req.ciphertext)

    # Decrypt MFCC
    decrypted_bytes = decrypt(key, iv, ciphertext)

    # Deserialize MFCC back into a Python object
    mfcc = pickle.loads(decrypted_bytes)
    mfcc = np.array(mfcc)

    if mfcc.shape != (20, 216):
        return {"error": f"Invalid MFCC shape {mfcc.shape}"}

    file_path = os.path.join(DATA_DIR, f"{req.user_id}.npy")

    # Enroll if not already
    if not os.path.exists(file_path):
        np.save(file_path, mfcc)
        return {"status": "enrolled", "user": req.user_id}

    # Authenticate if enrolled
    stored = np.load(file_path)

    distance = compare_mfcc(mfcc, stored)

    THRESHOLD = 50 # threshold for MFCC match -- may need tuning

    if distance < THRESHOLD:
        return {
            "status": "authenticated",
            "distance": float(distance)
        }
    else:
        return {
            "status": "rejected",
            "distance": float(distance)
        }
    
@app.post("/send-message")
def send_message(req: MessageRequest):
    # Derive shared key
    key = derive_key(req.client_pub_key.encode())
    print("Received message: ", req.ciphertext, "\n")

    # Decode
    iv = base64.b64decode(req.iv)
    ciphertext = base64.b64decode(req.ciphertext)
    print("Decoded ciphertext: ", ciphertext, "\n")

    # Decrypt
    decrypted_bytes = decrypt(key, iv, ciphertext)

    # Deserialize
    data = pickle.loads(decrypted_bytes)

    sender = data["sender"]
    recipient = data["recipient"]
    message = data["message"]

    # Check recipient exists
    file_path = os.path.join(DATA_DIR, f"{recipient}.npy")

    if not os.path.exists(file_path):
        return {"status": "failed", "reason": "recipient not found"}

    print(f"\n📩 MESSAGE RECEIVED")
    print(f"From: {sender}")
    print(f"To: {recipient}")
    print(f"Message: {message}")

    return {"status": "sent", "to": recipient}