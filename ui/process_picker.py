"""Process picker dialog — fast Treeview + icon on selection."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from core.process_enum import RunningProcess, list_running_processes, resolve_process_path
from ui.icon_loader import get_tk_image
from ui.theme import (
    ACCENT,
    BG_CARD,
    BG_DARK,
    BG_INPUT,
    FONT_BODY,
    FONT_SMALL,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class ProcessPickerDialog(ctk.CTkToplevel):
    def __init__(self, master, on_select, existing: set[str]) -> None:
        super().__init__(master)
        self._on_select = on_select
        self._existing = {e.lower() for e in existing}
        self._processes: list[RunningProcess] = []
        self._filtered: list[RunningProcess] = []
        self._icon_ref: tk.PhotoImage | None = None
        self._filter_job: str | None = None

        self.title("Processes")
        self.geometry("480x400")
        self.minsize(420, 320)
        self.configure(fg_color=BG_DARK)
        self.transient(master)
        self.grab_set()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 4))
        self._search = ctk.CTkEntry(
            top,
            placeholder_text="Filter...",
            height=28,
            fg_color=BG_INPUT,
            border_color=ACCENT,
            font=FONT_SMALL,
        )
        self._search.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._search.bind("<KeyRelease>", self._schedule_filter)
        ctk.CTkButton(
            top,
            text="↻",
            width=36,
            height=28,
            fg_color=ACCENT,
            text_color=BG_DARK,
            command=self._reload_async,
        ).pack(side="right")

        body = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        body.pack(fill="both", expand=True, padx=10, pady=4)

        list_frame = tk.Frame(body, bg=BG_CARD)
        list_frame.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Proc.Treeview",
            background=BG_DARK,
            fieldbackground=BG_DARK,
            foreground=TEXT_PRIMARY,
            rowheight=22,
            font=("Segoe UI", 10),
        )
        style.configure("Proc.Treeview.Heading", font=("Segoe UI", 9, "bold"))

        self._tree = ttk.Treeview(
            list_frame,
            columns=("name",),
            show="tree",
            selectmode="browse",
            style="Proc.Treeview",
            height=14,
        )
        self._tree.column("#0", width=28, stretch=False)
        self._tree.column("name", width=300, stretch=True)
        self._tree.heading("#0", text="")
        self._tree.heading("name", text="Process")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select_row)
        self._tree.bind("<Double-1>", self._on_double_click)

        self._preview = ctk.CTkFrame(body, fg_color=BG_DARK, width=140, corner_radius=8)
        self._preview.pack(side="right", fill="y", padx=6, pady=6)
        self._preview.pack_propagate(False)
        self._icon_label = ctk.CTkLabel(self._preview, text="", width=32, height=32)
        self._icon_label.pack(pady=(12, 4))
        self._name_label = ctk.CTkLabel(
            self._preview,
            text="—",
            font=FONT_SMALL,
            text_color=TEXT_PRIMARY,
            wraplength=120,
        )
        self._name_label.pack(padx=6)
        self._path_label = ctk.CTkLabel(
            self._preview,
            text="",
            font=("Consolas", 8),
            text_color=TEXT_MUTED,
            wraplength=120,
        )
        self._path_label.pack(padx=6, pady=4)

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(
            foot,
            text="Add",
            width=90,
            height=28,
            fg_color=ACCENT,
            text_color=BG_DARK,
            font=FONT_SMALL,
            command=self._confirm_selection,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            foot,
            text="Cancel",
            width=80,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=TEXT_MUTED,
            text_color=TEXT_SECONDARY,
            font=FONT_SMALL,
            command=self.destroy,
        ).pack(side="right")

        self._status = ctk.CTkLabel(
            self,
            text="Loading...",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self._status.pack(pady=(0, 6))

        self.after(50, self._reload_async)

    def _schedule_filter(self, _event=None) -> None:
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(120, self._apply_filter)

    def _reload_async(self) -> None:
        self._status.configure(text="Loading processes...")
        self._tree.delete(*self._tree.get_children())

        def work() -> None:
            try:
                procs = list_running_processes(resolve_paths=False)
            except OSError as e:
                procs = []
                self.after(0, lambda: self._status.configure(text=str(e)))
                return
            self.after(0, lambda: self._set_processes(procs))

        import threading

        threading.Thread(target=work, daemon=True).start()

    def _set_processes(self, procs: list[RunningProcess]) -> None:
        self._processes = procs
        self._status.configure(text=f"{len(procs)} processes")
        self._apply_filter()

    def _apply_filter(self) -> None:
        q = self._search.get().strip().lower()
        self._tree.delete(*self._tree.get_children())
        self._filtered = []
        for p in self._processes:
            if p.name.lower() in self._existing:
                continue
            if q and q not in p.name.lower():
                continue
            self._filtered.append(p)
            self._tree.insert("", "end", iid=p.name, text=" ", values=(p.name,))
        self._status.configure(text=f"{len(self._filtered)} shown")

    def _proc_by_name(self, name: str) -> RunningProcess | None:
        for p in self._filtered:
            if p.name == name:
                return p
        return None

    def _on_select_row(self, _event=None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        name = sel[0]
        proc = self._proc_by_name(name)
        if not proc:
            return
        self._name_label.configure(text=proc.name)
        self._path_label.configure(text="")
        self._load_icon_async(proc)

    def _load_icon_async(self, proc: RunningProcess) -> None:
        def work() -> None:
            path = proc.path if proc.path and "\\" in proc.path else proc.name
            if not proc.path or proc.path == proc.name:
                full = resolve_process_path(proc.pid)
                if full:
                    path = full
            icon = get_tk_image(path)
            self.after(0, lambda: self._show_icon(icon, path))

        import threading

        threading.Thread(target=work, daemon=True).start()

    def _show_icon(self, icon: tk.PhotoImage | None, path: str) -> None:
        name = self._name_label.cget("text")
        if icon is not None:
            self._icon_ref = icon
            self._icon_label.configure(image=icon, text="")
        else:
            self._icon_label.configure(image=None, text=_proc_initials(name))
        short = path if len(path) <= 80 else "…" + path[-77:]
        self._path_label.configure(text=short or "—")

    def _on_double_click(self, _event=None) -> None:
        self._confirm_selection()

    def _confirm_selection(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        self._on_select(sel[0])
        self.destroy()


def _proc_initials(name: str) -> str:
    base = name.replace(".exe", "").replace(".EXE", "")
    return (base[:2] or "?").upper()
