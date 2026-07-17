"""Engine registry: pick a generation backend by name or automatically."""

from .. import config
from .ace_step import AceStepEngine
from .base import GenerationRequest, GenerationResult, MusicEngine
from .mock import MockEngine
from .replicate_engine import ReplicateEngine

__all__ = [
    "GenerationRequest",
    "GenerationResult",
    "MusicEngine",
    "get_engine",
    "list_engines",
]

_ENGINES: dict[str, MusicEngine] = {}


def _registry() -> dict[str, MusicEngine]:
    if not _ENGINES:
        for engine in (AceStepEngine(), ReplicateEngine(), MockEngine()):
            _ENGINES[engine.name] = engine
    return _ENGINES


def list_engines() -> list[dict]:
    return [e.info() for e in _registry().values()]


def get_engine(name: str | None = None) -> MusicEngine:
    registry = _registry()
    name = name or config.DEFAULT_ENGINE
    if name and name != "auto":
        engine = registry.get(name)
        if engine is None:
            raise ValueError(f"Unknown engine: {name}")
        if not engine.is_available():
            raise RuntimeError(
                f"Engine '{name}' is not installed. "
                "Install model dependencies: pip install -r requirements-models.txt"
            )
        return engine
    # auto: prefer the best available engine
    for candidate in ("ace_step", "replicate", "mock"):
        if registry[candidate].is_available():
            return registry[candidate]
    return registry["mock"]
