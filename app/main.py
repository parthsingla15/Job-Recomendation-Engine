from fastapi import FastAPI

app = FastAPI(title="Job Match API")

@app.get("/health")
def health():
    return {"status": "ok"}