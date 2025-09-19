"""Rhythm bank manager handling persistence on disk."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Mapping, Optional

from . import RHYTHMS_ROOT
from .models import Rhythm, SectionType


METADATA_FILENAME = "metadata.json"


def sanitize_filename(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in ("_", "-", "."))


class RhythmBank:
    """Manage rhythms stored inside the :mod:`rhythms/` directory."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or RHYTHMS_ROOT
        self.root.mkdir(exist_ok=True)

    def list_rhythms(self):
        rhythms = []
        for entry in sorted(self.root.iterdir()):
            if not entry.is_dir():
                continue
            metadata_file = entry / METADATA_FILENAME
            if not metadata_file.exists():
                continue
            with metadata_file.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            rhythm = Rhythm.from_dict(payload)
            rhythms.append(rhythm.metadata)
        return rhythms

    def load(self, name: str) -> Rhythm:
        directory = self.root / name
        metadata_file = directory / METADATA_FILENAME
        if not metadata_file.exists():
            raise FileNotFoundError(f"Rhythm '{name}' does not exist")
        with metadata_file.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        rhythm = Rhythm.from_dict(payload)
        for section_meta in rhythm.sections.values():
            if section_meta.file_path is None:
                continue
            section_meta.file_path = Path(section_meta.file_path)
        return rhythm

    def save(self, rhythm: Rhythm, source_files: Optional[Mapping[SectionType, Path]] = None) -> Rhythm:
        directory = self.root / sanitize_filename(rhythm.metadata.name)
        directory.mkdir(parents=True, exist_ok=True)
        source_files = dict(source_files or {})
        for section, metadata in rhythm.sections.items():
            if section in source_files:
                source = Path(source_files[section])
                if not source.exists():
                    raise FileNotFoundError(source)
                destination = directory / sanitize_filename(source.name)
                shutil.copy2(source, destination)
                metadata.file_path = destination.relative_to(directory)
            elif metadata.file_path is not None:
                path = Path(metadata.file_path)
                metadata.file_path = (
                    path if not path.is_absolute() else path.relative_to(directory)
                )
        metadata_file = directory / METADATA_FILENAME
        with metadata_file.open("w", encoding="utf-8") as fh:
            json.dump(rhythm.to_dict(), fh, indent=2)
        return rhythm

    def delete(self, name: str) -> None:
        directory = self.root / name
        if directory.exists():
            shutil.rmtree(directory)

    def ensure(self, name: str) -> Rhythm:
        try:
            return self.load(name)
        except FileNotFoundError:
            rhythm = Rhythm.empty(name)
            self.save(rhythm)
            return rhythm


__all__ = ["RhythmBank", "METADATA_FILENAME"]
