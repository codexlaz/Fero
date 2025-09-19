"""Main Tkinter application window wiring the UI to the backend."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Optional

from ..models import Rhythm, SectionType
from ..player import Player, PlayerError
from ..rhythm_bank import RhythmBank
from .rhythm_editor import RhythmEditorDialog


class RhythmManagerApp(tk.Tk):
    def __init__(self, bank: Optional[RhythmBank] = None, player: Optional[Player] = None) -> None:
        super().__init__()
        self.title("Rhythm Bank")
        self.geometry("900x600")

        self.bank = bank or RhythmBank()
        self.player = player or Player()
        self.rhythms: Dict[str, Rhythm] = {}
        self.current_rhythm: Optional[Rhythm] = None

        self.tempo_var = tk.DoubleVar(value=120.0)
        self.time_signature_var = tk.StringVar(value="4/4")

        self._build_layout()
        self._refresh_rhythm_list()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Rhythms").pack(anchor=tk.W)
        self.listbox = tk.Listbox(left, height=20, width=25)
        self.listbox.pack(fill=tk.Y, expand=False)
        self.listbox.bind("<<ListboxSelect>>", self._on_rhythm_selected)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=5)
        ttk.Button(buttons, text="New", command=self._on_new).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Edit", command=self._on_edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Delete", command=self._on_delete).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        metadata_frame = ttk.LabelFrame(right, text="Metadata", padding=10)
        metadata_frame.pack(fill=tk.X)

        ttk.Label(metadata_frame, text="Tempo (BPM):").grid(row=0, column=0, sticky=tk.W)
        tempo_scale = ttk.Scale(
            metadata_frame,
            from_=40,
            to=240,
            variable=self.tempo_var,
            command=lambda _: self._on_tempo_change(),
            orient=tk.HORIZONTAL,
            length=200,
        )
        tempo_scale.grid(row=0, column=1, sticky=tk.EW, padx=5)
        ttk.Label(metadata_frame, textvariable=self.tempo_var).grid(row=0, column=2, sticky=tk.W)

        ttk.Label(metadata_frame, text="Time Signature:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(metadata_frame, textvariable=self.time_signature_var).grid(row=1, column=1, sticky=tk.W)

        playback_frame = ttk.LabelFrame(right, text="Sections", padding=10)
        playback_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.section_buttons: Dict[SectionType, ttk.Button] = {}
        for idx, section in enumerate(SectionType.ordered()):
            button = ttk.Button(
                playback_frame,
                text=section.value.replace("_", " ").title(),
                command=lambda s=section: self._on_section_pressed(s),
            )
            button.grid(row=idx // 3, column=idx % 3, padx=5, pady=5, sticky=tk.EW)
            self.section_buttons[section] = button

        control_frame = ttk.Frame(right)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(control_frame, text="Play Intro", command=lambda: self._play_preferred_intro()).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(control_frame, text="Stop", command=self._on_stop).pack(side=tk.LEFT, padx=5)

    # Rhythm management -----------------------------------------------------------------

    def _refresh_rhythm_list(self) -> None:
        self.listbox.delete(0, tk.END)
        self.rhythms.clear()
        for metadata in self.bank.list_rhythms():
            self.listbox.insert(tk.END, metadata.name)
            try:
                self.rhythms[metadata.name] = self.bank.load(metadata.name)
            except FileNotFoundError:
                continue

    def _on_rhythm_selected(self, event: Optional[tk.Event]) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        name = self.listbox.get(index)
        rhythm = self.rhythms.get(name)
        if not rhythm:
            try:
                rhythm = self.bank.load(name)
                self.rhythms[name] = rhythm
            except Exception as exc:
                messagebox.showerror("Load failed", str(exc), parent=self)
                return
        self.current_rhythm = rhythm
        self._apply_rhythm(rhythm)

    def _apply_rhythm(self, rhythm: Rhythm) -> None:
        self.tempo_var.set(rhythm.metadata.tempo_bpm)
        self.time_signature_var.set(rhythm.metadata.time_signature.to_string())
        try:
            self.player.load_rhythm(rhythm)
            self.player.set_tempo(rhythm.metadata.tempo_bpm)
        except PlayerError as exc:
            messagebox.showerror("Player error", str(exc), parent=self)

    def _on_new(self) -> None:
        dialog = RhythmEditorDialog(self, self.bank)
        rhythm = dialog.show()
        if rhythm:
            self._refresh_rhythm_list()

    def _on_edit(self) -> None:
        if not self.current_rhythm:
            messagebox.showinfo("Edit Rhythm", "Select a rhythm first.", parent=self)
            return
        dialog = RhythmEditorDialog(self, self.bank, self.current_rhythm)
        rhythm = dialog.show()
        if rhythm:
            self._refresh_rhythm_list()

    def _on_delete(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("Delete Rhythm", "Select a rhythm first.", parent=self)
            return
        name = self.listbox.get(selection[0])
        if not messagebox.askyesno("Confirm", f"Delete rhythm '{name}'?", parent=self):
            return
        self.bank.delete(name)
        self.current_rhythm = None
        self._refresh_rhythm_list()

    # Playback --------------------------------------------------------------------------

    def _on_section_pressed(self, section: SectionType) -> None:
        if self.current_rhythm is None:
            messagebox.showinfo("Playback", "Select a rhythm first.", parent=self)
            return
        try:
            if section in SectionType.mains():
                self.player.queue_section(section)
            else:
                self.player.play_section(section)
        except PlayerError as exc:
            messagebox.showerror("Playback failed", str(exc), parent=self)

    def _play_preferred_intro(self) -> None:
        if self.current_rhythm is None:
            messagebox.showinfo("Playback", "Select a rhythm first.", parent=self)
            return
        for section in SectionType.intros():
            if self.current_rhythm.sections.get(section) and self.current_rhythm.sections[section].file_path:
                try:
                    self.player.play_section(section, loop=False)
                except PlayerError as exc:
                    messagebox.showerror("Playback failed", str(exc), parent=self)
                return
        messagebox.showinfo("Playback", "No intro sections with audio are available.", parent=self)

    def _on_stop(self) -> None:
        try:
            self.player.stop()
        except PlayerError as exc:
            messagebox.showerror("Stop failed", str(exc), parent=self)

    def _on_tempo_change(self) -> None:
        value = self.tempo_var.get()
        try:
            self.player.set_tempo(value)
        except PlayerError:
            pass

    def _on_close(self) -> None:
        try:
            self.player.close()
        finally:
            self.destroy()


__all__ = ["RhythmManagerApp"]


def main() -> None:
    app = RhythmManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
