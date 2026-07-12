"""Background generation queue. One worker thread serializes GPU jobs."""

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

from . import audio_utils, config, database, engines

log = logging.getLogger("musicai.jobs")

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="musicai-gen")


def submit(track_id: str) -> None:
    database.update_track(track_id, status="queued")
    _executor.submit(_run, track_id)


def _run(track_id: str) -> None:
    track = database.get_track(track_id)
    if track is None:
        return
    database.update_track(track_id, status="generating")
    try:
        engine = engines.get_engine(track["engine"] or None)
        import json

        extra = json.loads(track["params"] or "{}")
        request = engines.GenerationRequest(
            prompt=track["prompt"],
            lyrics=track["lyrics"],
            duration=float(track["duration"] or 60.0),
            seed=extra.pop("seed", None),
            extra=extra,
        )
        result = engine.generate(request)

        wav_path = config.AUDIO_DIR / f"{track_id}.wav"
        duration = audio_utils.save_master_wav(result.audio, result.sample_rate, wav_path)

        database.update_track(
            track_id,
            status="done",
            audio_path=str(wav_path),
            duration=duration,
            engine=engine.name,
            error="",
        )
        log.info("track %s generated with %s (%.1fs)", track_id, engine.name, duration)
    except Exception as exc:  # pragma: no cover - defensive
        log.error("generation failed for %s:\n%s", track_id, traceback.format_exc())
        database.update_track(track_id, status="error", error=str(exc))
