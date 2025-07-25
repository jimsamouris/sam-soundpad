import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, filedialog
import pygame
import keyboard
import json
import os
import threading
import shutil
from pydub import AudioSegment

# Αρχικοποίηση pygame mixer
pygame.mixer.init()

KEYBINDS_FILE = "keybinds.json"
SOUNDS_DIR = "sounds"
SETTINGS_FILE = "settings.json"
DEFAULT_VOLUME = 0.5

if not os.path.exists(SOUNDS_DIR):
    os.makedirs(SOUNDS_DIR)

class SoundboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sam's Soundboard")

        self.keybinds = self.load_keybinds()
        self.settings = self.load_settings()

        self.hotkeys_active = False
        self.loaded_sounds = {}
        self.currently_playing = None
        self.registered_hotkeys = set()


        self.apply_theme()

        # GUI Setup
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.log = scrolledtext.ScrolledText(self.main_frame, width=60, height=15, state='disabled')
        self.log.pack(pady=10)

        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack()

        tk.Button(btn_frame, text="Show Keybinds", command=self.show_keybinds).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Import MP3", command=self.import_mp3).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Add / Change Keybind", command=self.set_keybind).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Delete Keybind", command=self.delete_keybind).grid(row=0, column=3, padx=5)

        self.start_btn = tk.Button(btn_frame, text="Start Soundboard", command=self.toggle_soundboard)
        self.start_btn.grid(row=0, column=4, padx=5)

        tk.Button(self.main_frame, text="Settings", command=self.open_settings_window).pack(pady=5)

        volume_frame = tk.Frame(root)
        volume_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        tk.Label(volume_frame, text="Volume").pack()
        self.volume_slider = tk.Scale(volume_frame, from_=1.0, to=0.0, resolution=0.1,
                                      orient=tk.VERTICAL, length=150)
        self.volume_slider.set(DEFAULT_VOLUME)
        self.volume_slider.pack()

    def log_message(self, msg):
        self.log.config(state='normal')
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state='disabled')

    def load_keybinds(self):
        if os.path.exists(KEYBINDS_FILE):
            with open(KEYBINDS_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_keybinds(self):
        with open(KEYBINDS_FILE, "w") as f:
            json.dump(self.keybinds, f, indent=4)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {
            "dark_theme": False,
            "normalize_volume": True
        }

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

    def apply_theme(self):
        if self.settings.get("dark_theme"):
            self.root.tk_setPalette(background="#2e2e2e", foreground="white", activeBackground="#444", activeForeground="white")
        else:
            self.root.tk_setPalette(background="SystemButtonFace", foreground="black")

    def open_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("250x150")
        win.transient(self.root)

        dark_var = tk.BooleanVar(value=self.settings.get("dark_theme"))
        norm_var = tk.BooleanVar(value=self.settings.get("normalize_volume"))

        tk.Checkbutton(win, text="Enable Dark Theme", variable=dark_var).pack(anchor="w", pady=5, padx=10)
        tk.Checkbutton(win, text="Auto Normalize MP3 Volume (reduce volume if too loud)", variable=norm_var).pack(anchor="w", pady=5, padx=10)

        def save_and_close():
            self.settings["dark_theme"] = dark_var.get()
            self.settings["normalize_volume"] = norm_var.get()
            self.save_settings()
            self.apply_theme()  # Άμεση εφαρμογή θέματος
            win.destroy()

        tk.Button(win, text="Save", command=save_and_close).pack(pady=10)

    def import_mp3(self):
        files = filedialog.askopenfilenames(title="Select MP3 files", filetypes=[("MP3 files", "*.mp3")])
        if not files:
            return
        imported = 0
        for f in files:
            filename = os.path.basename(f)
            dest = os.path.join(SOUNDS_DIR, filename)
            if not os.path.exists(dest):
                if self.settings.get("normalize_volume"):
                    try:
                        audio = AudioSegment.from_mp3(f)
                        loudness = audio.dBFS
                        if loudness > -3.0:
                            self.log_message(f"{filename} is loud ({loudness:.1f} dB), lowering -5dB")
                            audio = audio - 5
                        # Αν θέλεις μπορείς να αφαιρέσεις το boost για ήσυχα αρχεία
                        audio.export(dest, format="mp3")
                    except Exception as e:
                        self.log_message(f"Failed to normalize {filename}: {e}")
                        continue
                else:
                    shutil.copy(f, dest)
                imported += 1
        self.log_message(f"Imported {imported} file(s).")

    def show_keybinds(self):
        if not self.keybinds:
            self.log_message("No keybinds set.")
            return
        self.log_message("Current keybinds:")
        for key, sound in self.keybinds.items():
            self.log_message(f"{key} -> {sound}")

    def set_keybind(self):
        key = simpledialog.askstring("Set Keybind", "Press the key you want to bind:")
        if not key:
            return
        key = key.strip().lower()

        try:
            files = os.listdir(SOUNDS_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list sounds directory: {e}")
            return

        mp3_files = [f for f in files if f.endswith(".mp3")]
        if not mp3_files:
            messagebox.showerror("Error", f"No mp3 files found in {SOUNDS_DIR}")
            return

        choices = "\n".join(f"{i+1}. {f}" for i, f in enumerate(mp3_files))
        sound_choice = simpledialog.askstring("Select Sound", f"Available sounds:\n{choices}\n\nType the number:")
        if not sound_choice or not sound_choice.isdigit() or not (1 <= int(sound_choice) <= len(mp3_files)):
            messagebox.showerror("Error", "Invalid selection.")
            return

        selected_file = mp3_files[int(sound_choice)-1]
        self.keybinds[key] = os.path.join(SOUNDS_DIR, selected_file)
        self.save_keybinds()
        self.log_message(f"Bound '{key}' to '{selected_file}'")

    def delete_keybind(self):
        key = simpledialog.askstring("Delete Keybind", "Enter key to unbind:")
        if not key:
            return
        key = key.strip().lower()
        if key in self.keybinds:
            del self.keybinds[key]
            self.save_keybinds()
            self.log_message(f"Unbound '{key}'")
        else:
            messagebox.showerror("Error", "Key not found.")

    def play_sound(self, path):
        try:
            if self.currently_playing:
                self.currently_playing.stop()
            sound = pygame.mixer.Sound(path)
            volume = self.volume_slider.get()
            sound.set_volume(volume)
            sound.play()
            self.currently_playing = sound
        except Exception as e:
            self.log_message(f"Error playing sound: {e}")

    def start_hotkeys(self):
    # Αφαίρεσε όλες τις προηγούμενες hotkeys χειροκίνητα
     for hk in list(self.registered_hotkeys):
        keyboard.remove_hotkey(hk)
     self.registered_hotkeys.clear()

     for key, path in self.keybinds.items():
        hk = keyboard.add_hotkey(key, lambda p=path: self.play_sound(p))
        self.registered_hotkeys.add(hk)

     self.log_message("Soundboard started. Press ESC to stop.")

     def wait_for_esc():
        keyboard.wait("esc")
        self.stop_hotkeys()

     threading.Thread(target=wait_for_esc, daemon=True).start()
     self.hotkeys_active = True
     self.start_btn.config(text="Stop Soundboard")


    def stop_hotkeys(self):
     for hk in list(self.registered_hotkeys):
        keyboard.remove_hotkey(hk)
     self.registered_hotkeys.clear()
 
     self.hotkeys_active = False
     self.log_message("Soundboard stopped.")
     self.start_btn.config(text="Start Soundboard")

    def toggle_soundboard(self):
        if self.hotkeys_active:
            self.stop_hotkeys()
        else:
            self.start_hotkeys()


if __name__ == "__main__":
    root = tk.Tk()
    app = SoundboardApp(root)
    root.mainloop()
