
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageSequence, ImageOps
import serial
import threading
import urllib.request
import io
import struct
import time
from datetime import datetime


# =========================================================
# DESKBUDDY SETTINGS
# =========================================================

WIDTH = 128
GIF_HEIGHT = 112
FRAME_SIZE = WIDTH * GIF_HEIGHT * 2

CHUNK_SIZE = 1024
BAUD_RATE = 460800

SERIAL_TIMEOUT = 0.2
HANDSHAKE_TIMEOUT = 25
ACK_TIMEOUT = 12
DONE_TIMEOUT = 20

GIF_INTERVAL = 0.05

running = True
connected = False
playing = False

ser = None

gif_frames = []
frame_index = 0

state_lock = threading.Lock()
serial_lock = threading.Lock()


# =========================================================
# GUI
# =========================================================

root = tk.Tk()
root.title("DeskBuddy")
root.geometry("440x530")
root.resizable(False, False)
root.configure(bg="#080B12")

BG = "#080B12"
PANEL = "#111827"
ACCENT = "#39D5E8"
WHITE = "#F2F6FC"
MUTED = "#8291A5"
GREEN = "#43D19E"
RED = "#FF647C"

style = ttk.Style()
style.theme_use("clam")
style.configure(
    "Desk.Horizontal.TProgressbar",
    troughcolor="#202B3B",
    background=ACCENT,
    bordercolor="#202B3B",
    lightcolor=ACCENT,
    darkcolor=ACCENT
)

tk.Label(
    root,
    text="DESKMATE",
    bg=BG,
    fg=WHITE,
    font=("Segoe UI", 23, "bold")
).pack(pady=(20, 0))

tk.Label(
    root,
    text="ESP32 DESKTOP COMPANION",
    bg=BG,
    fg=ACCENT,
    font=("Segoe UI", 9, "bold")
).pack(pady=(0, 18))


# Connection panel
connection_panel = tk.Frame(root, bg=PANEL)
connection_panel.pack(fill="x", padx=22, pady=6)

tk.Label(
    connection_panel,
    text="SERIAL PORT",
    bg=PANEL,
    fg=MUTED,
    font=("Segoe UI", 9, "bold")
).pack(anchor="w", padx=14, pady=(12, 4))

port_entry = tk.Entry(
    connection_panel,
    bg="#202B3B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    font=("Segoe UI", 11)
)
port_entry.insert(0, "COM3")
port_entry.pack(fill="x", padx=14, ipady=7)

connect_button = tk.Button(
    connection_panel,
    text="CONNECT TO ESP32",
    bg=ACCENT,
    fg="#071018",
    activebackground="#7CEAF5",
    relief="flat",
    font=("Segoe UI", 10, "bold"),
    command=lambda: connect_esp()
)
connect_button.pack(fill="x", padx=14, pady=12, ipady=5)


# GIF panel
gif_panel = tk.Frame(root, bg=PANEL)
gif_panel.pack(fill="x", padx=22, pady=10)

tk.Label(
    gif_panel,
    text="GIF SOURCE",
    bg=PANEL,
    fg=MUTED,
    font=("Segoe UI", 9, "bold")
).pack(anchor="w", padx=14, pady=(12, 5))

url_entry = tk.Entry(
    gif_panel,
    bg="#202B3B",
    fg=WHITE,
    insertbackground=WHITE,
    relief="flat",
    font=("Segoe UI", 10)
)
url_entry.pack(fill="x", padx=14, ipady=7)

url_entry.insert(0, "Paste a direct GIF URL here")

load_button = tk.Button(
    gif_panel,
    text="LOAD GIF",
    bg="#26384B",
    fg=WHITE,
    activebackground="#344D66",
    relief="flat",
    font=("Segoe UI", 10, "bold"),
    command=lambda: load_gif()
)
load_button.pack(fill="x", padx=14, pady=10, ipady=5)


# Playback controls
control_panel = tk.Frame(root, bg=BG)
control_panel.pack(fill="x", padx=22, pady=5)

play_button = tk.Button(
    control_panel,
    text="PLAY",
    bg=GREEN,
    fg="#06130E",
    relief="flat",
    font=("Segoe UI", 10, "bold"),
    command=lambda: set_playing(True)
)
play_button.pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=8)

stop_button = tk.Button(
    control_panel,
    text="STOP",
    bg="#26384B",
    fg=WHITE,
    relief="flat",
    font=("Segoe UI", 10, "bold"),
    command=lambda: set_playing(False)
)
stop_button.pack(side="left", expand=True, fill="x", padx=(5, 0), ipady=8)


# Status
status_label = tk.Label(
    root,
    text="Waiting for connection",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 10)
)
status_label.pack(pady=(16, 4))

progress = ttk.Progressbar(
    root,
    style="Desk.Horizontal.TProgressbar",
    maximum=100,
    value=0
)
progress.pack(fill="x", padx=22, pady=5)

tk.Label(
    root,
    text="128 × 112 GIF  |  RGB565  |  ESP32",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 8)
).pack(pady=12)


# =========================================================
# GUI SAFE UPDATES
# =========================================================

def set_status(message, color=MUTED):
    if running:
        root.after(
            0,
            lambda: status_label.config(text=message, fg=color)
        )


def set_progress(value):
    if running:
        root.after(
            0,
            lambda: progress.config(value=value)
        )


# =========================================================
# SERIAL PROTOCOL
# =========================================================

def read_response(expected, timeout):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not running:
            raise RuntimeError("Application closing")

        line = ser.readline().decode(
            "utf-8", errors="ignore"
        ).strip()

        if not line:
            continue

        if line == expected:
            return

        if line.startswith("ERR_"):
            raise RuntimeError("ESP32 reported: " + line)

        # Ignore unrelated startup/debug lines.

    raise TimeoutError(
        "Timed out waiting for " + expected
    )


def send_clock():
    now = datetime.now()

    clock_text = now.strftime("%H:%M")
    date_text = now.strftime("%a, %d %b %Y").upper()

    packet = f"T|{clock_text}|{date_text}\n"

    ser.write(packet.encode("utf-8"))
    read_response("CLOCK_OK", 5)


def send_gif_frame(frame_data):
    if len(frame_data) != FRAME_SIZE:
        raise ValueError(
            f"Invalid frame size: {len(frame_data)} bytes"
        )

    # Ask ESP32 to prepare for a frame.
    ser.write(b"G\n")

    # Do not send image data until ESP32 is ready.
    read_response("FRAME_READY", HANDSHAKE_TIMEOUT)

    total_chunks = (FRAME_SIZE + CHUNK_SIZE - 1) // CHUNK_SIZE

    for chunk_number in range(total_chunks):
        start = chunk_number * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, FRAME_SIZE)

        chunk = frame_data[start:end]

        ser.write(chunk)

        # ESP32 acknowledges each received chunk.
        read_response("ACK", ACK_TIMEOUT)

        set_progress(
            int((chunk_number + 1) * 100 / total_chunks)
        )

    # Wait until the complete frame is drawn.
    read_response("DONE", DONE_TIMEOUT)

    set_progress(0)


# =========================================================
# RGB565 CONVERSION
# =========================================================

def image_to_rgb565(image):
    image = image.convert("RGB")
    pixels = image.load()

    output = bytearray(FRAME_SIZE)
    offset = 0

    for y in range(GIF_HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixels[x, y]

            value = (
                ((r & 0xF8) << 8)
                | ((g & 0xFC) << 3)
                | (b >> 3)
            )

            struct.pack_into("<H", output, offset, value)
            offset += 2

    return bytes(output)


# =========================================================
# GIF LOADING
# =========================================================

def decode_gif(data):
    image = Image.open(io.BytesIO(data))

    frames = []

    for frame in ImageSequence.Iterator(image):
        converted = frame.convert("RGB")

        fitted = ImageOps.fit(
            converted,
            (WIDTH, GIF_HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        frames.append(image_to_rgb565(fitted))

        if len(frames) >= 60:
            break

    if not frames:
        raise ValueError("No GIF frames found")

    return frames


def load_gif():
    global gif_frames, frame_index

    url = url_entry.get().strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        messagebox.showerror(
            "Invalid URL",
            "Enter a direct GIF URL."
        )
        return

    load_button.config(state="disabled")
    set_status("Downloading GIF...", ACCENT)

    def worker():
        global gif_frames, frame_index

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(
                request, timeout=25
            ) as response:
                data = response.read()

            frames = decode_gif(data)

            with state_lock:
                gif_frames = frames
                frame_index = 0

            set_status(
                f"GIF loaded successfully - {len(frames)} frames",
                GREEN
            )

        except Exception as error:
            set_status("GIF loading failed", RED)
            root.after(
                0,
                lambda: messagebox.showerror(
                    "GIF Error", str(error)
                )
            )

        finally:
            if running:
                root.after(
                    0,
                    lambda: load_button.config(state="normal")
                )

    threading.Thread(target=worker, daemon=True).start()


# =========================================================
# PLAYBACK
# =========================================================

def set_playing(value):
    global playing

    with state_lock:
        if value and not gif_frames:
            messagebox.showinfo(
                "DeskBuddy",
                "Load a GIF first."
            )
            return

        playing = value

    if value:
        set_status("GIF playback enabled", GREEN)
    else:
        set_status("GIF playback paused", MUTED)


# =========================================================
# CONNECT AND COMMUNICATION WORKER
# =========================================================

def connect_esp():
    global connected, ser

    if connected:
        return

    port = port_entry.get().strip()

    if not port:
        messagebox.showerror(
            "DeskBuddy",
            "Enter your ESP32 COM port."
        )
        return

    connect_button.config(state="disabled")
    set_status("Connecting to ESP32...", ACCENT)

    def worker():
        global connected, ser, frame_index

        try:
            ser = serial.Serial(
                port=port,
                baudrate=BAUD_RATE,
                timeout=SERIAL_TIMEOUT,
                write_timeout=10
            )

            # Opening the port normally resets the ESP32.
            # Wait for its startup READY message.
            read_response("READY", HANDSHAKE_TIMEOUT)

            send_clock()

            connected = True

            set_status("ESP32 connected successfully", GREEN)

            last_clock_update = time.monotonic()

            while running and connected:

                # Read playback state safely.
                with state_lock:
                    should_play = playing
                    frames_available = bool(gif_frames)

                    if should_play and frames_available:
                        frame = gif_frames[frame_index]
                        frame_index = (
                            frame_index + 1
                        ) % len(gif_frames)
                    else:
                        frame = None

                # Clock is updated between frames only.
                if time.monotonic() - last_clock_update >= 5:
                    send_clock()
                    last_clock_update = time.monotonic()

                if frame is not None:
                    set_status("Sending GIF frame...", ACCENT)

                    send_gif_frame(frame)

                    set_status("DeskBuddy is running", GREEN)

                    time.sleep(GIF_INTERVAL)

                else:
                    time.sleep(0.05)

        except Exception as error:
            connected = False
            set_status("Connection error: " + str(error), RED)

        finally:
            connected = False

            try:
                if ser and ser.is_open:
                    ser.close()
            except Exception:
                pass

            if running:
                root.after(
                    0,
                    lambda: connect_button.config(state="normal")
                )

    threading.Thread(target=worker, daemon=True).start()


# =========================================================
# CLOSE
# =========================================================

def close_app():
    global running, connected, playing

    running = False
    connected = False
    playing = False

    try:
        if ser and ser.is_open:
            ser.close()
    except Exception:
        pass

    root.destroy()


root.protocol("WM_DELETE_WINDOW", close_app)
root.mainloop()
