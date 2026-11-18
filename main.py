import os
import sys

# ============================================================
# Détection mode .exe (PyInstaller) vs mode développement
# À FAIRE AVANT tout import de database
# ============================================================
if getattr(sys, 'frozen', False):
    # Mode .exe : on se place dans le dossier de l'exécutable
    os.chdir(os.path.dirname(sys.executable))
    os.environ.setdefault("DATABASE_URL", "sqlite:///./app.db")
    os.environ.setdefault("SECRET_KEY", "change-me-en-production-1234567890")
    BUNDLE_DIR = sys._MEIPASS
else:
    # Mode développement : dossier du fichier main.py
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Imports (après la détection mode)
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import Base, engine
import models  # noqa: F401 — force le chargement des tables

from routers import (
    auth, clients, produits, stock, ventes,
    commissions, paiements, dashboard, notifications,
    admin, stats, stats_advanced, stats_client, commandes,
)

# ============================================================
# App FastAPI
# ============================================================
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HABIT MANAGER", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploads (photos de profil)
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ============================================================
# ROUTERS API
# ============================================================
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(produits.router)
app.include_router(stock.router)
app.include_router(ventes.router)
app.include_router(commissions.router)
app.include_router(paiements.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(stats.router)
app.include_router(stats_advanced.router)
app.include_router(stats_client.router)
app.include_router(commandes.router)

# ============================================================
# FRONTEND REACT (build dans /static)
# ============================================================
STATIC_DIR = os.path.join(BUNDLE_DIR, "static")

if os.path.isdir(STATIC_DIR):
    # Servir les assets (JS, CSS)
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback : toutes les routes non-API renvoient index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            from fastapi import HTTPException
            raise HTTPException(404, "Not found")

        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)

        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
else:
    # Mode dev : pas de static → simple status
    @app.get("/")
    def root():
        return {"status": "ok", "message": "API HABIT APP (dev mode)"}


# ============================================================
# Lancement standalone (.exe)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")

    threading.Timer(2.5, open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")