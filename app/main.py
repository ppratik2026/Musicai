"""MusicAI — open-source music generation studio.

Run with:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import audio_utils, config, database, engines, jobs

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="MusicAI", version="1.0.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
def startup() -> None:
    database.init_db()


class GenerateBody(BaseModel):
    prompt: str = Field(..., min_length=1, description="Style tags / description, e.g. 'lofi hindi pop, warm female vocals, 90 bpm'")
    lyrics: str = ""
    title: str = "Untitled"
    artist: str = ""
    album: str = ""
    genre: str = ""
    duration: float = Field(60.0, ge=5)
    engine: str = "auto"
    seed: int | None = None
    guidance_scale: float | None = None


class MetadataBody(BaseModel):
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    genre: str | None = None


@app.get("/api/engines")
def api_engines():
    return {"default": config.DEFAULT_ENGINE, "engines": engines.list_engines()}


@app.post("/api/generate")
def api_generate(body: GenerateBody):
    if body.duration > config.MAX_DURATION_SECONDS:
        raise HTTPException(400, f"duration must be <= {config.MAX_DURATION_SECONDS}s")
    params: dict = {}
    if body.seed is not None:
        params["seed"] = body.seed
    if body.guidance_scale is not None:
        params["guidance_scale"] = body.guidance_scale
    track = database.create_track(
        title=body.title.strip() or "Untitled",
        artist=body.artist.strip(),
        album=body.album.strip(),
        genre=body.genre.strip(),
        prompt=body.prompt.strip(),
        lyrics=body.lyrics.strip(),
        engine="" if body.engine == "auto" else body.engine,
        duration=body.duration,
        params=params,
    )
    jobs.submit(track["id"])
    return {"track": database.get_track(track["id"])}


@app.get("/api/tracks")
def api_tracks():
    return {"tracks": database.list_tracks()}


@app.get("/api/tracks/{track_id}")
def api_track(track_id: str):
    track = database.get_track(track_id)
    if track is None:
        raise HTTPException(404, "track not found")
    return {"track": track}


@app.patch("/api/tracks/{track_id}")
def api_update_track(track_id: str, body: MetadataBody):
    track = database.get_track(track_id)
    if track is None:
        raise HTTPException(404, "track not found")
    fields = {k: v.strip() for k, v in body.model_dump().items() if v is not None}
    if fields:
        database.update_track(track_id, **fields)
    return {"track": database.get_track(track_id)}


@app.delete("/api/tracks/{track_id}")
def api_delete_track(track_id: str):
    track = database.get_track(track_id)
    if track is None:
        raise HTTPException(404, "track not found")
    for suffix in (".wav", ".mp3", ".flac"):
        path = config.AUDIO_DIR / f"{track_id}{suffix}"
        path.unlink(missing_ok=True)
    (config.COVER_DIR / f"{track_id}.jpg").unlink(missing_ok=True)
    database.delete_track(track_id)
    return {"ok": True}


@app.post("/api/tracks/{track_id}/retry")
def api_retry(track_id: str):
    track = database.get_track(track_id)
    if track is None:
        raise HTTPException(404, "track not found")
    jobs.submit(track_id)
    return {"track": database.get_track(track_id)}


@app.post("/api/tracks/{track_id}/cover")
async def api_upload_cover(track_id: str, file: UploadFile):
    track = database.get_track(track_id)
    if track is None:
        raise HTTPException(404, "track not found")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "cover image too large (max 10 MB)")
    cover_path = config.COVER_DIR / f"{track_id}.jpg"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(data)
    database.update_track(track_id, cover_path=str(cover_path))
    return {"track": database.get_track(track_id)}


@app.get("/api/tracks/{track_id}/audio")
def api_audio(track_id: str):
    """Stream the master WAV for in-browser playback."""
    track = database.get_track(track_id)
    if track is None or not track["audio_path"]:
        raise HTTPException(404, "audio not ready")
    return FileResponse(track["audio_path"], media_type="audio/wav")


@app.get("/api/tracks/{track_id}/download")
def api_download(track_id: str, fmt: str = "wav"):
    """Download a distribution-ready file: wav (master), mp3 320k, or flac.

    mp3/flac get metadata + cover art embedded so stores display them.
    """
    track = database.get_track(track_id)
    if track is None or not track["audio_path"]:
        raise HTTPException(404, "audio not ready")
    try:
        path = audio_utils.export_format(Path(track["audio_path"]), fmt)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc))

    if path.suffix != ".wav":
        cover = Path(track["cover_path"]) if track["cover_path"] else None
        audio_utils.tag_file(
            path,
            title=track["title"],
            artist=track["artist"] or "MusicAI",
            album=track["album"],
            genre=track["genre"],
            cover_path=cover,
        )

    safe_title = "".join(c for c in track["title"] if c.isalnum() or c in " -_").strip() or track_id
    media = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac"}[path.suffix[1:]]
    return FileResponse(path, media_type=media, filename=f"{safe_title}{path.suffix}")


# Serve the frontend at / (mounted last so /api/* wins).
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
