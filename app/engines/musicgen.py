"""MusicGen backend — high-quality instrumental music from a text prompt.

Uses Meta's MusicGen through Hugging Face `transformers`. The code is
open source, but note that the released MusicGen *weights* are licensed
CC-BY-NC 4.0 (non-commercial). Great for drafts and personal projects;
for tracks you plan to sell or distribute, use the ACE-Step engine.
"""

import importlib.util

import numpy as np

from .. import config
from .base import GenerationRequest, GenerationResult, MusicEngine


class MusicGenEngine(MusicEngine):
    name = "musicgen"
    display_name = "MusicGen (instrumental)"
    description = (
        "Meta's MusicGen: instrumental music from a text description. "
        "Weights are CC-BY-NC (non-commercial) — use ACE-Step for releases."
    )
    supports_vocals = False
    license = "MIT code, CC-BY-NC-4.0 weights"
    commercial_use = False

    def __init__(self) -> None:
        self._model = None
        self._processor = None

    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("transformers") is not None
            and importlib.util.find_spec("torch") is not None
        )

    def _load(self):
        if self._model is None:
            import torch
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            self._processor = AutoProcessor.from_pretrained(config.MUSICGEN_MODEL)
            self._model = MusicgenForConditionalGeneration.from_pretrained(config.MUSICGEN_MODEL)
            if torch.cuda.is_available():
                self._model = self._model.to("cuda")
        return self._model, self._processor

    def generate(self, request: GenerationRequest) -> GenerationResult:
        import torch

        model, processor = self._load()
        if request.seed is not None:
            torch.manual_seed(request.seed)

        inputs = processor(text=[request.prompt], padding=True, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # MusicGen emits ~50 tokens per second of audio.
        max_new_tokens = min(int(request.duration * 50), 1500)
        with torch.no_grad():
            audio_values = model.generate(
                **inputs,
                do_sample=True,
                guidance_scale=float(request.extra.get("guidance_scale", 3.0)),
                max_new_tokens=max_new_tokens,
            )

        sample_rate = model.config.audio_encoder.sampling_rate
        audio = audio_values[0].cpu().float().numpy()  # (channels, samples)
        audio = np.transpose(audio)
        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        peak = float(np.max(np.abs(audio))) or 1.0
        if peak > 1.0:
            audio = audio / peak
        return GenerationResult(audio=audio.astype(np.float32), sample_rate=sample_rate)
