from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "IoT Auth Server Running"}

@app.get("/health")
def health():
    return {"status": "ok"}