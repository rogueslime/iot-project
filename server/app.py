from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import os

app = FastAPI()

# Folder to store MFCC files
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Define expected request format
class MFCCRequest(BaseModel):
    user_id: str
    mfcc: list  # 2D list

@app.get("/")
def root():
    return {"message": "IoT Auth Server Running"}

@app.post("/upload")
def upload_mfcc(data: MFCCRequest):
    # Convert list → NumPy array
    mfcc_array = np.array(data.mfcc)

    # Build filename (one per user)
    file_path = os.path.join(DATA_DIR, f"{data.user_id}.npy")

    # Save MFCC
    np.save(file_path, mfcc_array)

    return {
        "status": "saved",
        "user": data.user_id,
        "shape": mfcc_array.shape
    }