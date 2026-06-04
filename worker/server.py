import threading

from fastapi import FastAPI

from worker.runner import run_worker

app = FastAPI(title="TacticAI Worker")


@app.on_event("startup")
async def startup() -> None:
    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()


@app.get("/health")
def health() -> dict:
    return {"ok": True}
