import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import PORT
from src.db import create_db
from src.routes.detect import router
from src.routes.retrieval import retrieval_router

# ============================================================
# APP
# ============================================================

app = FastAPI(title="Agentic Honeypot API")
app.include_router(router)
app.include_router(retrieval_router)
create_db()

# ============================================================
# DASHBOARD
# ============================================================

_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"
)


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, access_log=False)