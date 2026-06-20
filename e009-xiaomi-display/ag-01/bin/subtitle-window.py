#!/usr/bin/env python3
import tkinter as tk
import threading
import time
import os

LOG = "/tmp/virt-subtitles.log"

class SubtitleApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Asistente - Subtitulos")
        self.root.geometry("700x300+10+1300")
        self.root.configure(bg="#1a1a2e")
        self.root.attributes("-topmost", True)

        self.label = tk.Label(
            self.root,
            text="Iniciando...",
            font=("Segoe UI", 16),
            fg="#eee",
            bg="#1a1a2e",
            wraplength=680,
            justify="left",
            anchor="nw",
            padx=15,
            pady=10,
        )
        self.label.pack(fill="both", expand=True)

        self.update_log()

    def update_log(self):
        try:
            if os.path.exists(LOG):
                with open(LOG) as f:
                    lines = f.read().strip().split("\n")
                text = "\n".join(lines[-8:])
                if text:
                    self.label.config(text=text)
        except:
            pass
        self.root.after(1500, self.update_log)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    SubtitleApp().run()
