import uvicorn
from fastapi import FastAPI

from src.config import PORT
from src.routes.detect import router

# ============================================================
# APP
# ============================================================

app = FastAPI(title="Agentic Honeypot API")
app.include_router(router)

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, access_log=False)