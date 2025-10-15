# server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import ALLOWED_ORIGINS
from api.routes import router
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Wave Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_folder = os.path.join(os.path.dirname(__file__), "dist")

# Mount React assets (JS, CSS, images, etc.)
app.mount("/assets", StaticFiles(directory=os.path.join(static_folder, "assets")), name="assets")

# Serve React index.html for all other routes (frontend routing)
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    index_path = os.path.join(static_folder, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}
