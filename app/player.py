"""Audio playback engine for Yamaha-style rhythms."""
from __future__ import annotations

import threading
from queue import Empty, Queue
from typing import Dict, Optional, Tuple

import numpy as np

from .models import Rhythm, SectionMetadata, SectionType

try:
    import librosa
except ImportError:  # pragma: no cover - optional dependency
    librosa = None  # type: ignore

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency
    sd = None  # type: ignore

DEFAULT_SAMPLE_RATE = 44100
CROSSFADE_DURATION = 0.1  # seconds


class PlayerError(RuntimeError):
    """Raised when playback operations cannot be performed."""


class Player:
    """Manage section playback, tempo changes and Yamaha fill logic."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._command_queue: "Queue[Tuple[str, Optional[SectionType], bool]]" = Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._rhythm: Optional[Rhythm] = None
        self._original_audio: Dict[SectionType, np.ndarray] = {}
        self._stretched_audio: Dict[SectionType, np.ndarray] = {}
        self._sample_rate = DEFAULT_SAMPLE_RATE
        self._current_section: Optional[SectionType] = None
        self._current_tempo: Optional[float] = None
        self._crossfade_samples = int(CROSSFADE_DURATION * self._sample_rate)

    def load_rhythm(self, rhythm: Rhythm) -> None:
        with self._lock:
            self._rhythm = rhythm
            self._current_tempo = rhythm.metadata.tempo_bpm
            self._original_audio.clear()
            self._stretched_audio.clear()
            for section, metadata in rhythm.sections.items():
                audio = self._load_audio(metadata)
                if audio is None:
                    continue
                self._original_audio[section] = audio
                self._stretched_audio[section] = audio

    def set_tempo(self, tempo_bpm: float) -> None:
        with self._lock:
            if self._rhythm is None:
                raise PlayerError("No rhythm loaded")
            if tempo_bpm <= 0:
                raise PlayerError("Tempo must be greater than zero")
            self._current_tempo = tempo_bpm
            reference_tempo = self._rhythm.metadata.tempo_bpm
            ratio = tempo_bpm / reference_tempo
            self._stretched_audio = {
                section: self._time_stretch(audio, ratio)
                for section, audio in self._original_audio.items()
            }
            self._command_queue.put(("tempo", None, False))

    def play_section(self, section: SectionType, loop: bool = True) -> None:
        self._command_queue.put(("play", section, loop))

    def queue_section(self, section: SectionType, loop: bool = True) -> None:
        if section in SectionType.mains() and self._current_section in SectionType.mains():
            fill_map = {
                SectionType.MAIN_A: SectionType.FILL_A,
                SectionType.MAIN_B: SectionType.FILL_B,
                SectionType.MAIN_C: SectionType.FILL_C,
                SectionType.MAIN_D: SectionType.FILL_D,
            }
            fill_section = fill_map.get(section)
            if fill_section and fill_section in self._stretched_audio:
                self._command_queue.put(("play", fill_section, False))
        self._command_queue.put(("play", section, loop))

    def stop(self) -> None:
        self._command_queue.put(("stop", None, False))

    def close(self) -> None:
        self._command_queue.put(("shutdown", None, False))
        self._thread.join(timeout=2)

    # Internal helpers -----------------------------------------------------------------

    def _load_audio(self, metadata: SectionMetadata) -> Optional[np.ndarray]:
        if metadata.file_path is None:
            return None
        if librosa is None:
            raise PlayerError("librosa is required for audio loading")
        path = metadata.file_path
        y, sr = librosa.load(path, sr=DEFAULT_SAMPLE_RATE, mono=False)
        if y.ndim == 1:
            y = np.expand_dims(y, axis=0)
        self._sample_rate = sr
        self._crossfade_samples = int(CROSSFADE_DURATION * self._sample_rate)
        return y

    def _time_stretch(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        if librosa is None:
            raise PlayerError("librosa is required for time stretching")
        if np.isclose(ratio, 1.0):
            return audio
        stretched_channels = []
        for channel in audio:
            stretched_channels.append(librosa.effects.time_stretch(channel, rate=ratio))
        min_len = min(len(ch) for ch in stretched_channels)
        stretched = np.stack([ch[:min_len] for ch in stretched_channels], axis=0)
        return stretched

    def _apply_crossfade(self, previous: np.ndarray, next_audio: np.ndarray) -> np.ndarray:
        if previous.size == 0 or next_audio.size == 0:
            return next_audio
        overlap = min(self._crossfade_samples, previous.shape[1], next_audio.shape[1])
        if overlap <= 0:
            return np.concatenate([previous, next_audio], axis=1)
        fade_out = np.linspace(1.0, 0.0, overlap)
        fade_in = np.linspace(0.0, 1.0, overlap)
        crossfaded = previous.copy()
        crossfaded[:, -overlap:] = (
            crossfaded[:, -overlap:] * fade_out + next_audio[:, :overlap] * fade_in
        )
        remainder = next_audio[:, overlap:]
        if remainder.size > 0:
            crossfaded = np.concatenate([crossfaded, remainder], axis=1)
        return crossfaded

    def _run(self) -> None:
        buffer: Optional[np.ndarray] = None
        looping = False
        while True:
            try:
                command, section, loop_flag = self._command_queue.get(timeout=0.1)
            except Empty:
                continue
            if command == "shutdown":
                break
            if command == "stop":
                buffer = None
                looping = False
                if sd:
                    sd.stop()
                continue
            if command == "tempo":
                buffer = None
                looping = False
                continue
            if command == "play" and section is not None:
                audio = self._stretched_audio.get(section)
                if audio is None:
                    continue
                if buffer is not None:
                    audio = self._apply_crossfade(buffer, audio)
                buffer = audio
                looping = loop_flag
                self._current_section = section
                self._play_buffer(buffer, looping)
        if sd:
            sd.stop()

    def _play_buffer(self, audio: np.ndarray, loop: bool) -> None:
        if sd is None:
            raise PlayerError(
                "sounddevice is required for playback. Install it to enable audio output."
            )
        data = audio.T
        sd.stop()
        if loop:
            repeated = np.tile(data, (100, 1))
            sd.play(repeated, samplerate=self._sample_rate, blocking=False)
        else:
            sd.play(data, samplerate=self._sample_rate, blocking=False)


__all__ = ["Player", "PlayerError"]
