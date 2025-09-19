"""Tkinter dialog for editing rhythm metadata and sections."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Dict, Optional

from ..models import Rhythm, RhythmMetadata, SectionMetadata, SectionType, TimeSignature
from ..rhythm_bank import RhythmBank


class RhythmEditorDialog:
    def __init__(self, master: tk.Tk, bank: RhythmBank, rhythm: Optional[Rhythm] = None) -> None:
        self.bank = bank
        self.master = master
        self.rhythm = rhythm or Rhythm.empty("New Rhythm")
        self.result: Optional[Rhythm] = None

        self.window = tk.Toplevel(master)
        self.window.title("Rhythm Editor")
        self.window.transient(master)
        self.window.grab_set()

        self.name_var = tk.StringVar(value=self.rhythm.metadata.name)
        self.tempo_var = tk.DoubleVar(value=self.rhythm.metadata.tempo_bpm)
        self.timesig_var = tk.StringVar(value=self.rhythm.metadata.time_signature.to_string())
        self.section_vars: Dict[SectionType, tk.StringVar] = {}

        self._build_form()
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_form(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky=tk.EW)

        ttk.Label(frame, text="Tempo (BPM):").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.tempo_var, width=10).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(frame, text="Time signature:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=self.timesig_var, width=10).grid(row=2, column=1, sticky=tk.W)

        sections_frame = ttk.LabelFrame(frame, text="Sections", padding=10)
        sections_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=(10, 0))
        sections_frame.columnconfigure(1, weight=1)

        for row, section in enumerate(SectionType.ordered()):
            label = section.value.replace("_", " ").title()
            ttk.Label(sections_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar()
            metadata = self.rhythm.sections.get(section)
            if metadata and metadata.file_path:
                var.set(str(metadata.file_path))
            entry = ttk.Entry(sections_frame, textvariable=var, width=40)
            entry.grid(row=row, column=1, sticky=tk.EW, padx=(5, 5))
            button = ttk.Button(
                sections_frame,
                text="Browse",
                command=lambda s=section, v=var: self._browse_file(s, v),
            )
            button.grid(row=row, column=2, padx=(0, 5))
            self.section_vars[section] = var

        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(actions, text="Save", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _browse_file(self, section: SectionType, var: tk.StringVar) -> None:
        filename = filedialog.askopenfilename(
            parent=self.window,
            title=f"Select WAV file for {section.value}",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if filename:
            var.set(filename)

    def _on_cancel(self) -> None:
        self.window.destroy()

    def _on_save(self) -> None:
        try:
            tempo = float(self.tempo_var.get())
        except (TypeError, ValueError):
            messagebox.showerror("Invalid tempo", "Tempo must be a number.", parent=self.window)
            return
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Invalid name", "Name cannot be empty.", parent=self.window)
            return
        try:
            timesig = TimeSignature.from_string(self.timesig_var.get())
        except Exception as exc:  # pragma: no cover - validation feedback
            messagebox.showerror("Invalid time signature", str(exc), parent=self.window)
            return

        metadata = RhythmMetadata(name=name, tempo_bpm=tempo, time_signature=timesig)
        sections: Dict[SectionType, SectionMetadata] = {}
        sources: Dict[SectionType, Path] = {}
        for section, var in self.section_vars.items():
            value = var.get().strip()
            if not value:
                sections[section] = SectionMetadata(section=section)
                continue
            path = Path(value)
            sections[section] = SectionMetadata(section=section, file_path=path)
            if path.exists():
                sources[section] = path
        rhythm = Rhythm(metadata=metadata, sections=sections)
        try:
            rhythm = self.bank.save(rhythm, sources)
        except Exception as exc:  # pragma: no cover - propagate errors to user
            messagebox.showerror("Save failed", str(exc), parent=self.window)
            return
        self.result = rhythm
        self.window.destroy()

    def show(self) -> Optional[Rhythm]:
        self.master.wait_window(self.window)
        return self.result
