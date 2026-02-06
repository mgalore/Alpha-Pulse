from fastapi import FastAPI
import logging

app = FastAPI(title="Alpha-Pulse API")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Alpha-Pulse Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
