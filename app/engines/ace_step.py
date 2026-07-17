"""ACE-Step backend — full songs with vocals and lyrics.

ACE-Step (https://github.com/ace-step/ACE-Step) is the leading open-source
song-generation model: text tags + lyrics in, a complete mixed song out.
Code and weights are Apache-2.0 licensed, so the output carries no watermark
and can be released commercially.

Install:  pip install -r requirements-models.txt   (needs a GPU with ~8 GB VRAM)
"""

import importlib.util
import tempfile
from pathlib import Path

import numpy as np

from .. import config
from .base import GenerationRequest, GenerationResult, MusicEngine


class AceStepEngine(MusicEngine):
    name = "ace_step"
    display_name = "ACE-Step (vocals + lyrics)"
    description = (
        "Open-source full-song generation: writes a complete mixed track with "
        "vocals from your style tags and lyrics. Closest open alternative to Suno."
    )
    supports_vocals = True
    license = "Apache-2.0 (code and weights)"
    commercial_use = True

    def __init__(self) -> None:
        self._pipeline = None

    def is_available(self) -> bool:
        return importlib.util.find_spec("acestep") is not None

    def _load(self):
        if self._pipeline is None:
            import os

            from acestep.pipeline_ace_step import ACEStepPipeline

            checkpoint_dir = Path(config.ACE_STEP_CHECKPOINT_DIR)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            # The constructor only maps "bfloat16"/"float32"; other dtypes
            # (e.g. float16 for T4-class GPUs) go through ACE-Step's own
            # ACE_PIPELINE_DTYPE override.
            dtype = config.ACE_STEP_DTYPE
            if dtype not in ("bfloat16", "float32"):
                os.environ["ACE_PIPELINE_DTYPE"] = dtype
                dtype = "float32"
            # Downloads checkpoints on first use when the directory is empty.
            self._pipeline = ACEStepPipeline(
                checkpoint_dir=str(checkpoint_dir),
                dtype=dtype,
                torch_compile=False,
                cpu_offload=config.ACE_STEP_CPU_OFFLOAD,
                quantized=config.ACE_STEP_QUANTIZED,
            )
        return self._pipeline

    def generate(self, request: GenerationRequest) -> GenerationResult:
        import soundfile as sf

        pipeline = self._load()
        with tempfile.TemporaryDirectory() as tmp:
            out_path = str(Path(tmp) / "output.wav")
            pipeline(
                audio_duration=float(request.duration),
                prompt=request.prompt,
                lyrics=request.lyrics or "[inst]",
                infer_step=int(request.extra.get("infer_step", 60)),
                guidance_scale=float(request.extra.get("guidance_scale", 15.0)),
                scheduler_type="euler",
                cfg_type="apg",
                omega_scale=10.0,
                manual_seeds=str(request.seed) if request.seed is not None else None,
                save_path=out_path,
                format="wav",
            )
            audio, sample_rate = sf.read(out_path, dtype="float32", always_2d=True)

        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        return GenerationResult(audio=audio, sample_rate=sample_rate)
