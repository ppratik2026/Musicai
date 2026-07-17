"""Replicate backend — cloud-hosted ACE-Step, no local GPU needed.

Perfect for deploying MusicAI on a normal (CPU-only) server like a
Hostinger/DigitalOcean VPS: the app runs on your server, generation runs
on Replicate's GPUs (~$0.03-0.06 per song, pay per second).

Setup:
  1. Create an account at https://replicate.com and add billing.
  2. Copy an API token from https://replicate.com/account/api-tokens
  3. export REPLICATE_API_TOKEN=r8_...

The hosted model defaults to `lucataco/ace-step` (same open-source
Apache-2.0 ACE-Step weights, so outputs remain watermark-free and
commercially usable). Override with MUSICAI_REPLICATE_MODEL if needed;
if the model expects different input field names, adjust
MUSICAI_REPLICATE_INPUT_MAP (JSON, ours->theirs), e.g.
'{"prompt": "tags", "lyrics": "lyrics", "duration": "duration"}'.
"""

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

from .base import GenerationRequest, GenerationResult, MusicEngine

API_BASE = os.environ.get("MUSICAI_REPLICATE_API_BASE", "https://api.replicate.com")
MODEL = os.environ.get("MUSICAI_REPLICATE_MODEL", "lucataco/ace-step")
INPUT_MAP = json.loads(
    os.environ.get(
        "MUSICAI_REPLICATE_INPUT_MAP",
        '{"prompt": "tags", "lyrics": "lyrics", "duration": "duration", "seed": "seed"}',
    )
)
POLL_INTERVAL = 3.0
TIMEOUT_SECONDS = 15 * 60


class ReplicateEngine(MusicEngine):
    name = "replicate"
    display_name = "Replicate cloud (ACE-Step, no GPU)"
    description = (
        "Runs the open-source ACE-Step model on Replicate's cloud GPUs — full "
        "songs with vocals, no local GPU needed. Pay per song (~$0.03-0.06)."
    )
    supports_vocals = True
    license = "Apache-2.0 model via Replicate"
    commercial_use = True

    def is_available(self) -> bool:
        return bool(os.environ.get("REPLICATE_API_TOKEN"))

    def _api(self, method: str, path: str, payload: dict | None = None) -> dict:
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={
                "Authorization": f"Bearer {os.environ['REPLICATE_API_TOKEN']}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Replicate API error {exc.code}: {detail}") from exc

    def generate(self, request: GenerationRequest) -> GenerationResult:
        import soundfile as sf

        inputs: dict = {}
        values = {
            "prompt": request.prompt,
            "lyrics": request.lyrics or "[inst]",
            "duration": float(request.duration),
            "seed": request.seed,
        }
        for ours, theirs in INPUT_MAP.items():
            if values.get(ours) is not None:
                inputs[theirs] = values[ours]

        prediction = self._api("POST", f"/v1/models/{MODEL}/predictions", {"input": inputs})

        started = time.time()
        while prediction.get("status") in (None, "starting", "processing"):
            if time.time() - started > TIMEOUT_SECONDS:
                raise RuntimeError("Replicate prediction timed out")
            time.sleep(POLL_INTERVAL)
            prediction = self._api("GET", f"/v1/predictions/{prediction['id']}")

        if prediction.get("status") != "succeeded":
            raise RuntimeError(f"Replicate prediction failed: {prediction.get('error') or prediction.get('status')}")

        output = prediction.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
        if isinstance(output, dict):
            output = output.get("audio") or output.get("url") or next(iter(output.values()), None)
        if not isinstance(output, str):
            raise RuntimeError(f"Unexpected Replicate output: {type(output).__name__}")

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "output_audio"
            with urllib.request.urlopen(output, timeout=300) as resp:
                audio_path.write_bytes(resp.read())
            try:
                audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
            except Exception:
                # Not a libsndfile-readable format (e.g. some mp3s) — convert.
                import shutil
                import subprocess

                ffmpeg = shutil.which("ffmpeg")
                if ffmpeg is None:
                    raise RuntimeError("Could not read Replicate audio output (install ffmpeg)")
                wav_path = Path(tmp) / "converted.wav"
                subprocess.run([ffmpeg, "-y", "-i", str(audio_path), str(wav_path)], check=True, capture_output=True)
                audio, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=True)

        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        return GenerationResult(audio=audio, sample_rate=sample_rate)
