"""Engine interface. Every generation backend implements this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class GenerationRequest:
    prompt: str
    lyrics: str = ""
    duration: float = 60.0
    seed: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    # Stereo float32 audio in [-1, 1], shape (num_samples, 2).
    audio: np.ndarray
    sample_rate: int


class MusicEngine(ABC):
    """A text (+ lyrics) to music generation backend."""

    name: str = "base"
    display_name: str = "Base"
    description: str = ""
    supports_vocals: bool = False
    license: str = ""
    commercial_use: bool = False

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this engine can run in the current environment."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate audio. Runs in a worker thread; may take minutes."""

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "supports_vocals": self.supports_vocals,
            "license": self.license,
            "commercial_use": self.commercial_use,
            "available": self.is_available(),
        }
