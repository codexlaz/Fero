"""Data models for rhythm metadata and sections."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional


class SectionType(str, Enum):
    """Known Yamaha-style rhythm sections."""

    INTRO_A = "intro_a"
    INTRO_B = "intro_b"
    INTRO_C = "intro_c"
    INTRO_D = "intro_d"
    MAIN_A = "main_a"
    MAIN_B = "main_b"
    MAIN_C = "main_c"
    MAIN_D = "main_d"
    FILL_A = "fill_a"
    FILL_B = "fill_b"
    FILL_C = "fill_c"
    FILL_D = "fill_d"
    BREAK = "break"
    ENDING_A = "ending_a"
    ENDING_B = "ending_b"
    ENDING_C = "ending_c"

    @classmethod
    def mains(cls) -> List["SectionType"]:
        return [cls.MAIN_A, cls.MAIN_B, cls.MAIN_C, cls.MAIN_D]

    @classmethod
    def fills(cls) -> List["SectionType"]:
        return [cls.FILL_A, cls.FILL_B, cls.FILL_C, cls.FILL_D]

    @classmethod
    def intros(cls) -> List["SectionType"]:
        return [cls.INTRO_A, cls.INTRO_B, cls.INTRO_C, cls.INTRO_D]

    @classmethod
    def endings(cls) -> List["SectionType"]:
        return [cls.ENDING_A, cls.ENDING_B, cls.ENDING_C]

    @classmethod
    def ordered(cls) -> Iterable["SectionType"]:
        return (
            cls.INTRO_A,
            cls.INTRO_B,
            cls.INTRO_C,
            cls.INTRO_D,
            cls.MAIN_A,
            cls.MAIN_B,
            cls.MAIN_C,
            cls.MAIN_D,
            cls.FILL_A,
            cls.FILL_B,
            cls.FILL_C,
            cls.FILL_D,
            cls.BREAK,
            cls.ENDING_A,
            cls.ENDING_B,
            cls.ENDING_C,
        )


@dataclass
class TimeSignature:
    beats_per_bar: int
    beat_unit: int

    def to_string(self) -> str:
        return f"{self.beats_per_bar}/{self.beat_unit}"

    @classmethod
    def from_string(cls, value: str) -> "TimeSignature":
        num, denom = value.split("/", 1)
        return cls(beats_per_bar=int(num), beat_unit=int(denom))


@dataclass
class SectionMetadata:
    section: SectionType
    file_path: Optional[Path] = None

    def resolved_file(self, base_path: Optional[Path] = None) -> Optional[Path]:
        if self.file_path is None:
            return None
        path = Path(self.file_path)
        if not path.is_absolute() and base_path is not None:
            path = base_path / path
        return path


@dataclass
class RhythmMetadata:
    name: str
    tempo_bpm: float
    time_signature: TimeSignature


@dataclass
class Rhythm:
    metadata: RhythmMetadata
    sections: Dict[SectionType, SectionMetadata] = field(default_factory=dict)

    def available_sections(self) -> Iterable[SectionType]:
        return [section for section, data in self.sections.items() if data.file_path]

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.metadata.name,
            "tempo_bpm": self.metadata.tempo_bpm,
            "time_signature": self.metadata.time_signature.to_string(),
            "sections": {
                section.value: (
                    str(metadata.file_path) if metadata.file_path is not None else None
                )
                for section, metadata in self.sections.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Rhythm":
        time_signature = TimeSignature.from_string(str(payload["time_signature"]))
        metadata = RhythmMetadata(
            name=str(payload["name"]),
            tempo_bpm=float(payload["tempo_bpm"]),
            time_signature=time_signature,
        )
        sections_payload: Mapping[str, Optional[str]] = payload.get("sections", {})  # type: ignore[assignment]
        sections: Dict[SectionType, SectionMetadata] = {}
        for key, value in sections_payload.items():
            try:
                section_type = SectionType(key)
            except ValueError:
                continue
            sections[section_type] = SectionMetadata(
                section=section_type,
                file_path=Path(value) if value else None,
            )
        for section in SectionType.ordered():
            sections.setdefault(section, SectionMetadata(section=section))
        return cls(metadata=metadata, sections=sections)

    @classmethod
    def empty(cls, name: str) -> "Rhythm":
        metadata = RhythmMetadata(
            name=name,
            tempo_bpm=120.0,
            time_signature=TimeSignature(4, 4),
        )
        sections = {
            section: SectionMetadata(section=section)
            for section in SectionType.ordered()
        }
        return cls(metadata=metadata, sections=sections)
