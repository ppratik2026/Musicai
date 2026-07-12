"""Audio export and metadata tagging for distribution-ready masters."""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from . import config


def save_master_wav(audio: np.ndarray, sample_rate: int, out_path: Path) -> float:
    """Write a 44.1 kHz / 16-bit stereo WAV (the format distributors expect).

    Returns the duration in seconds.
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)

    if sample_rate != config.EXPORT_SAMPLE_RATE:
        audio = _resample(audio, sample_rate, config.EXPORT_SAMPLE_RATE)
        sample_rate = config.EXPORT_SAMPLE_RATE

    audio = np.clip(audio, -1.0, 1.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio, sample_rate, subtype="PCM_16")
    return len(audio) / sample_rate


def _resample(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Linear resampling; good enough here, models mostly emit 44.1/48 kHz."""
    n_out = int(round(len(audio) * sr_out / sr_in))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return np.stack(
        [np.interp(x_new, x_old, audio[:, ch]) for ch in range(audio.shape[1])],
        axis=1,
    ).astype(np.float32)


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def export_format(wav_path: Path, fmt: str) -> Path:
    """Convert the master WAV to mp3 or flac using ffmpeg (lazily, cached)."""
    fmt = fmt.lower()
    if fmt == "wav":
        return wav_path
    if fmt not in ("mp3", "flac"):
        raise ValueError(f"Unsupported format: {fmt}")

    out_path = wav_path.with_suffix(f".{fmt}")
    if out_path.exists() and out_path.stat().st_mtime >= wav_path.stat().st_mtime:
        return out_path

    ffmpeg = _ffmpeg()
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for mp3/flac export (apt install ffmpeg)")

    args = [ffmpeg, "-y", "-i", str(wav_path)]
    if fmt == "mp3":
        args += ["-codec:a", "libmp3lame", "-b:a", "320k"]
    args.append(str(out_path))
    subprocess.run(args, check=True, capture_output=True)
    return out_path


def tag_file(path: Path, title: str, artist: str, album: str, genre: str, cover_path: Path | None = None) -> None:
    """Embed ID3/Vorbis metadata (and cover art) so stores show correct info."""
    try:
        import mutagen
        from mutagen.flac import FLAC, Picture
        from mutagen.id3 import APIC, ID3, TALB, TCON, TIT2, TPE1
    except ImportError:
        return  # tagging is best-effort

    suffix = path.suffix.lower()
    cover_bytes = cover_path.read_bytes() if cover_path and cover_path.exists() else None

    if suffix == ".mp3":
        try:
            tags = ID3(str(path))
        except mutagen.MutagenError:
            tags = ID3()
        tags.setall("TIT2", [TIT2(encoding=3, text=title)])
        tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
        tags.setall("TALB", [TALB(encoding=3, text=album)])
        tags.setall("TCON", [TCON(encoding=3, text=genre)])
        if cover_bytes:
            tags.setall("APIC", [APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_bytes)])
        tags.save(str(path))
    elif suffix == ".flac":
        f = FLAC(str(path))
        f["title"], f["artist"], f["album"], f["genre"] = title, artist, album, genre
        if cover_bytes:
            pic = Picture()
            pic.type = 3
            pic.mime = "image/jpeg"
            pic.data = cover_bytes
            f.clear_pictures()
            f.add_picture(pic)
        f.save()
