"""Demo engine — procedural music synthesized with NumPy, no GPU required.

Lets you run and test the whole app (UI, library, exports, metadata) on any
machine. It picks a key, tempo and chord progression from your prompt text
and renders a simple synth arrangement: pads, bass, arpeggio and drums.
"""

import hashlib

import numpy as np

from .base import GenerationRequest, GenerationResult, MusicEngine

SR = 44100

# Chord progressions (scale degrees) to rotate through.
PROGRESSIONS = [
    [0, 5, 3, 4],   # i–VI–iv–v feel
    [0, 3, 4, 4],
    [0, 4, 5, 3],
    [5, 3, 0, 4],
]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


def _note_freq(semitones_from_a4: float) -> float:
    return 440.0 * (2.0 ** (semitones_from_a4 / 12.0))


def _adsr(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    env = np.ones(n, dtype=np.float32) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na, nd = min(na, n), min(nd, max(n - na, 0))
    nr = min(nr, n)
    if na:
        env[:na] = np.linspace(0, 1, na)
    if nd:
        env[na:na + nd] = np.linspace(1, s, nd)
    if nr:
        env[-nr:] *= np.linspace(1, 0, nr)
    return env


def _tone(freq: float, dur: float, shape: str = "saw", gain: float = 0.3) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    if shape == "saw":
        wave = 2.0 * ((t * freq) % 1.0) - 1.0
        wave += 0.5 * np.sin(2 * np.pi * freq * t)
    elif shape == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        wave = np.sin(2 * np.pi * freq * t)
    return (wave * gain).astype(np.float32)


class MockEngine(MusicEngine):
    name = "mock"
    display_name = "Demo synth (no GPU)"
    description = (
        "Procedurally synthesized placeholder music. Use it to try the app "
        "end-to-end without downloading any model."
    )
    supports_vocals = False
    license = "MIT (part of this app)"
    commercial_use = True

    def is_available(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        seed = request.seed
        if seed is None:
            digest = hashlib.sha256((request.prompt + request.lyrics).encode()).digest()
            seed = int.from_bytes(digest[:4], "big")
        rng = np.random.default_rng(seed)

        tempo = int(rng.integers(84, 126))
        root = int(rng.integers(-14, -2))  # around C3..A3
        progression = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]

        beat = 60.0 / tempo
        bar = 4 * beat
        total = max(8.0, min(float(request.duration), 300.0))
        n_total = int(total * SR)
        mix = np.zeros(n_total, dtype=np.float32)

        n_bars = int(np.ceil(total / bar))
        for b in range(n_bars):
            start = int(b * bar * SR)
            degree = progression[b % len(progression)]
            chord_root = root + MINOR_SCALE[degree % 7]
            chord = [chord_root, chord_root + 3, chord_root + 7]

            # Pad chord
            for semi in chord:
                tone = _tone(_note_freq(semi), bar, "saw", 0.10)
                tone *= _adsr(len(tone), 0.05, 0.2, 0.7, 0.3)
                end = min(start + len(tone), n_total)
                mix[start:end] += tone[: end - start]

            # Bass on each beat
            for i in range(4):
                s = start + int(i * beat * SR)
                tone = _tone(_note_freq(chord_root - 12), beat * 0.9, "sine", 0.28)
                tone *= _adsr(len(tone), 0.005, 0.1, 0.6, 0.1)
                end = min(s + len(tone), n_total)
                if end > s:
                    mix[s:end] += tone[: end - s]

            # Arpeggio, eighth notes
            for i in range(8):
                s = start + int(i * beat / 2 * SR)
                semi = chord[int(rng.integers(3))] + 12
                tone = _tone(_note_freq(semi), beat * 0.45, "square", 0.05)
                tone *= _adsr(len(tone), 0.002, 0.05, 0.4, 0.05)
                end = min(s + len(tone), n_total)
                if end > s:
                    mix[s:end] += tone[: end - s]

            # Drums: kick on 1 & 3, hat on eighths
            for i in range(8):
                s = start + int(i * beat / 2 * SR)
                if i % 4 == 0:
                    n = int(0.12 * SR)
                    t = np.arange(n) / SR
                    kick = np.sin(2 * np.pi * (90 * np.exp(-t * 18)) * t) * np.exp(-t * 22)
                    end = min(s + n, n_total)
                    if end > s:
                        mix[s:end] += (kick[: end - s] * 0.5).astype(np.float32)
                n = int(0.03 * SR)
                hat = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / (0.004 * SR))
                end = min(s + n, n_total)
                if end > s:
                    mix[s:end] += hat[: end - s] * 0.05

        # Fade in/out and normalize
        fade = int(0.5 * SR)
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)
        peak = float(np.max(np.abs(mix))) or 1.0
        mix = mix / peak * 0.85

        # Simple stereo widening: slightly delayed right channel
        delay = int(0.012 * SR)
        right = np.concatenate([np.zeros(delay, dtype=np.float32), mix[:-delay]])
        stereo = np.stack([mix, 0.7 * right + 0.3 * mix], axis=1)
        return GenerationResult(audio=stereo, sample_rate=SR)
