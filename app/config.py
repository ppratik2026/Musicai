"""Application configuration, driven by environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where generated audio and the track database live.
DATA_DIR = Path(os.environ.get("MUSICAI_DATA_DIR", BASE_DIR / "data"))
AUDIO_DIR = DATA_DIR / "audio"
COVER_DIR = DATA_DIR / "covers"
DB_PATH = DATA_DIR / "musicai.db"

# Default generation engine: "ace_step" (local GPU), "replicate"
# (cloud GPU), or "mock" (no GPU needed, for development).
DEFAULT_ENGINE = os.environ.get("MUSICAI_ENGINE", "auto")

# ACE-Step checkpoint directory (downloaded automatically on first run
# when empty).
ACE_STEP_CHECKPOINT_DIR = os.environ.get("MUSICAI_ACE_CHECKPOINT_DIR", str(BASE_DIR / "checkpoints" / "ace_step"))
# bfloat16 needs Ampere+ (A100/L4/RTX 30xx+); use float16 on older GPUs like T4.
ACE_STEP_DTYPE = os.environ.get("MUSICAI_ACE_DTYPE", "bfloat16")
# Offload idle model parts to CPU RAM — lets ACE-Step run on ~8 GB VRAM GPUs.
ACE_STEP_CPU_OFFLOAD = os.environ.get("MUSICAI_ACE_CPU_OFFLOAD", "0") == "1"
ACE_STEP_QUANTIZED = os.environ.get("MUSICAI_ACE_QUANTIZED", "0") == "1"
# Decode long songs in overlapping chunks instead of one giant tensor.
# Kicks in past ~48s of audio; without it, 3-minute songs exhaust GPU
# memory during decoding ("GET was unable to find an engine" cuDNN error).
ACE_STEP_OVERLAPPED_DECODE = os.environ.get("MUSICAI_ACE_OVERLAPPED_DECODE", "1") == "1"

# Distribution-ready master format: 44.1 kHz / 16-bit stereo WAV.
EXPORT_SAMPLE_RATE = 44100

MAX_DURATION_SECONDS = int(os.environ.get("MUSICAI_MAX_DURATION", "240"))

HOST = os.environ.get("MUSICAI_HOST", "0.0.0.0")
PORT = int(os.environ.get("MUSICAI_PORT", "8000"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, AUDIO_DIR, COVER_DIR):
        d.mkdir(parents=True, exist_ok=True)
