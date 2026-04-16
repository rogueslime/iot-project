from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import os
import base64
import pickle

from crypto_utils import derive_key, decrypt

app = FastAPI()

# Check for data directory
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

class AuthRequest(BaseModel):
    user_id: str
    client_pub_key: str
    iv: str
    ciphertext: str

# Calculate distance of MFCCs
def compare_mfcc(mfcc1, mfcc2):
    # Ensure same shape
    if mfcc1.shape != mfcc2.shape:
        return float("inf")

    return np.linalg.norm(mfcc1 - mfcc2)

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