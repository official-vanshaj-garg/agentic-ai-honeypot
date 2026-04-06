import uvicorn
from fastapi import FastAPI

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
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, access_log=False)