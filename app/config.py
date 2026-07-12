"""Application configuration, driven by environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where generated audio and the track database live.
DATA_DIR = Path(os.environ.get("MUSICAI_DATA_DIR", BASE_DIR / "data"))
AUDIO_DIR = DATA_DIR / "audio"
COVER_DIR = DATA_DIR / "covers"
DB_PATH = DATA_DIR / "musicai.db"

# Default generation engine: "ace_step" (full songs with vocals),
# "musicgen" (instrumental), or "mock" (no GPU needed, for development).
DEFAULT_ENGINE = os.environ.get("MUSICAI_ENGINE", "auto")

# ACE-Step checkpoint directory (downloaded automatically on first run
# when empty). MusicGen model name for the transformers/audiocraft backend.
ACE_STEP_CHECKPOINT_DIR = os.environ.get("MUSICAI_ACE_CHECKPOINT_DIR", str(BASE_DIR / "checkpoints" / "ace_step"))
MUSICGEN_MODEL = os.environ.get("MUSICAI_MUSICGEN_MODEL", "facebook/musicgen-small")

# Distribution-ready master format: 44.1 kHz / 16-bit stereo WAV.
EXPORT_SAMPLE_RATE = 44100

MAX_DURATION_SECONDS = int(os.environ.get("MUSICAI_MAX_DURATION", "240"))

HOST = os.environ.get("MUSICAI_HOST", "0.0.0.0")
PORT = int(os.environ.get("MUSICAI_PORT", "8000"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, AUDIO_DIR, COVER_DIR):
        d.mkdir(parents=True, exist_ok=True)
