"""
app.py – Plate Solver Microservice
Einziger Endpoint: POST /solve
Läuft auf 127.0.0.1:8011, nur lokal erreichbar.
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import uuid

from solver import solve, SolveError, ALLOWED_SUFFIXES

BASE_DIR   = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
APP_HOST   = "127.0.0.1"
APP_PORT   = 8011
MAX_MB     = 50


@asynccontextmanager
async def lifespan(app: FastAPI):
    IMAGES_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="Plate Solver Microservice", lifespan=lifespan)


@app.post("/solve")
async def solve_endpoint(file: UploadFile = File(...)):
    """
    Bild hochladen → plate-solven → JSON mit Koordinaten zurückgeben.
    Bild wird nach images/ gespeichert (für Debugging), aber nicht verwaltet.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Format '{suffix}' nicht unterstützt.")

    content = await file.read()
    if len(content) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"Datei zu groß (max {MAX_MB} MB).")

    dest = IMAGES_DIR / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(content)

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, solve, str(dest)
        )
        return JSONResponse({"ok": True, "original": file.filename, **result})

    except SolveError as e:
        raise HTTPException(422, str(e))

    except Exception as e:
        raise HTTPException(500, f"Interner Fehler: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, reload=False)
