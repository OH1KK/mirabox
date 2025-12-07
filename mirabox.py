#!/usr/bin/python3
# MiraBox Controller v0.2.0
# Clean folder layout, verbose debug, reliable dynamic updates

import signal, sys, os, json, time, subprocess, threading, argparse, shutil
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL.Image")

from StreamDock.DeviceManager import DeviceManager
from StreamDock.Devices.StreamDockN1 import StreamDockN1

__version__ = "0.2.0"

parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version=f"MiraBox Controller v{__version__}")
parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
parser.add_argument("--enable-networking", action="store_true", help="Enable HTTP API for dynamic updates")
args = parser.parse_args()

DEBUG = args.debug
ENABLE_NETWORKING = args.enable_networking

def log(*msg):
    if DEBUG:
        print("[DEBUG]", *msg)

# ==================== PATHS ====================
BASE_DIR   = "./dynamic"
IMAGE_DIR  = os.path.join(BASE_DIR, "button-images")
SET_DIR    = os.path.join(BASE_DIR, "button-sets")
DEFAULT_IMG = "./img/default-button.png"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(SET_DIR,   exist_ok=True)

NUM_SETS = 10
current_set = 0
sets = [None] * NUM_SETS
streamdocks = []
set_switch_in_progress = False
original_brightness = 10
flash_brightness = 75

DECK_ROTARY_CCW = 160
DECK_ROTARY_CW  = 161
LONG_PRESS_DURATION = 1.0
button_press_time = {}
BUTTON_COMMANDS = {}
device_lock = threading.Lock()

# ==================== LOAD SET (auto-repairs broken JSON) ====================
def load_set(n):
    fn = os.path.join(SET_DIR, f"button-set-{n}.json")
    log(f"Loading set {n} → {fn}")

    if not os.path.exists(fn):
        log("  File not found → empty set")
        return None

    try:
        with open(fn, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        log(f"  JSON error: {e}")
        return None

    # Normalise data – accept old/broken formats
    data = {"background": "./img/default-slider.png", "buttons": {}}
    if "background" in raw:
        data["background"] = raw["background"]
    if "buttons" in raw and isinstance(raw["buttons"], dict):
        data["buttons"].update(raw["buttons"])
    for k in raw:
        if k.isdigit() and isinstance(raw[k], dict):
            data["buttons"][k] = raw[k]

    bg = data.get("background", "./img/default-slider.png")
    buttons = {}

    for k, v in data.get("buttons", {}).items():
        try:
            key = int(k)
            if not 1 <= key <= 10:
                continue

            old_path = v.get("image", DEFAULT_IMG)
            new_path = os.path.join(IMAGE_DIR, f"{n}_{key}.png")

            # Migrate old external icons
            if old_path != new_path and os.path.exists(old_path) and not os.path.exists(new_path):
                try:
                    shutil.copy2(old_path, new_path)
                    log(f"  Migrated image → {new_path}")
                except Exception as e:
                    log(f"  Migration failed: {e}")

            final_path = new_path if os.path.exists(new_path) else old_path
            if not os.path.exists(final_path):
                final_path = DEFAULT_IMG
                log(f"  Button {key}: MISSING {os.path.basename(new_path)} → using default-button.png")
            else:
                log(f"  Button {key}: OK → {os.path.basename(final_path)}")

            buttons[key] = {
                "image": final_path,
                "command": v.get("command", []),
                "gui": v.get("gui", False)
            }
        except Exception as e:
            log(f"  Bad button entry {k}: {e}")

    log(f"Set {n} loaded → {len(buttons)} buttons")
    return {"bg": bg, "buttons": buttons}

# ==================== SAVE SET (always clean JSON) ====================
def save_set(idx):
    if not sets[idx]:
        return
    s = sets[idx]
    clean = {"background": s["bg"], "buttons": {}}
    for key, btn in s["buttons"].items():
        clean["buttons"][str(key)] = {
            "image": btn["image"],
            "command": btn.get("command", []),
            "gui": btn.get("gui", False)
        }
    fn = os.path.join(SET_DIR, f"button-set-{idx+1}.json")
    try:
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=4)
        log(f"Saved clean JSON → {fn}")
    except Exception as e:
        log(f"Save failed: {e}")

# ==================== APPLY SET (verbose) ====================
def apply_set(idx):
    global BUTTON_COMMANDS, set_switch_in_progress
    if not sets[idx]:
        log(f"Set {idx+1} is empty")
        set_switch_in_progress = False
        return

    s = sets[idx]
    BUTTON_COMMANDS.clear()
    for k, btn in s["buttons"].items():
        cmd = btn.get("command", [])
        if isinstance(cmd, list) and cmd and not isinstance(cmd[0], list):
            cmd = [cmd]
        BUTTON_COMMANDS[k] = (cmd, btn.get("gui", False))

    log(f"Applying Set {idx+1}...")
    with device_lock:
        for dev in streamdocks:
            bg_path = s["bg"] if os.path.exists(s["bg"]) else "./img/default-slider.png"
            log(f"  Background → {bg_path} {'(OK)' if os.path.exists(bg_path) else '(MISSING)'}")
            dev.set_touchscreen_image(bg_path)
            dev.refresh()
        time.sleep(1.8)

        for dev in streamdocks:
            for i in range(1, 11):
                path = s["buttons"].get(i, {}).get("image", DEFAULT_IMG)
                if not os.path.exists(path):
                    log(f"  Button {i}: NOT FOUND → {path} → using default")
                    path = DEFAULT_IMG
                else:
                    log(f"  Button {i}: OK → {os.path.basename(path)}")
                dev.set_key_image(i, path)
                dev.refresh()
            time.sleep(0.08)

    log(f"Set {idx+1} applied")
    with device_lock:
        for dev in streamdocks:
            dev.set_brightness(original_brightness)
    set_switch_in_progress = False

def flash_confirm():
    with device_lock:
        for dev in streamdocks:
            dev.set_brightness(flash_brightness)
    time.sleep(0.08)
    with device_lock:
        for dev in streamdocks:
            dev.set_brightness(original_brightness)

# ==================== HTTP API ====================
def start_http_api():
    if not ENABLE_NETWORKING:
        log("HTTP API disabled")
        return
    try:
        from flask import Flask, request
        import base64
        app = Flask(__name__)

        @app.route("/update/<int:set_num>/<int:key>", methods=["POST"])
        def update(set_num, key):
            if not (1 <= set_num <= 10 and 1 <= key <= 10):
                return "Invalid range", 400
            set_idx = set_num - 1

            data = request.data
            if not data and "image" in request.form:
                try:
                    data = base64.b64decode(request.form["image"])
                except:
                    return "Bad base64", 400
            if not data:
                return "No image data", 400

            filepath = os.path.join(IMAGE_DIR, f"{set_num}_{key}.png")
            try:
                with open(filepath, "wb") as f:
                    f.write(data)
                log(f"Received image → {os.path.basename(filepath)}")
            except Exception as e:
                log(f"Write error: {e}")
                return "Write failed", 500

            # Ensure set exists in memory
            if sets[set_idx] is None:
                sets[set_idx] = {"bg": "./img/default-slider.png", "buttons": {}}
            sets[set_idx]["buttons"].setdefault(key, {"command": [], "gui": False})
            sets[set_idx]["buttons"][key]["image"] = filepath

            save_set(set_idx)

            # Live update if this set is active
            if current_set == set_idx:
                with device_lock:
                    for dev in streamdocks:
                        dev.set_key_image(key, filepath)
                        dev.refresh()
                log(f"Live updated button {key} on set {set_num}")

            return "OK", 200

        @app.route("/update/<int:key>", methods=["POST"])
        def update_current(key):
            return update(current_set + 1, key)

        threading.Thread(
            target=lambda: app.run(host="::", port=8333, debug=False, use_reloader=False),
            daemon=True
        ).start()
        log("HTTP API listening on http://[::]:8333/update/<set>/<key>")

    except ImportError:
        log("Flask not found – install with: pip3 install flask")

# ==================== EVENT HANDLING ====================
class SilentCapture:
    def __init__(self):
        self.original = sys.stdout

    def write(self, text):
        line = text.rstrip("\n")
        if "Acknowledgement: ACK" in line:
            try:
                parts = line.split(", ")
                key = int(parts[2].split(": ")[1])
                status = int(parts[3].split(": ")[1])
                self._handle(key, status)
            except: pass
        if DEBUG:
            self.original.write(text)

    def flush(self):
        self.original.flush()

    def _handle(self, key, status):
        now = time.time()
        global current_set, set_switch_in_progress

        if status == 1 and 1 <= key <= 10:
            button_press_time[key] = now
            flash_confirm()

        elif status == 0 and key in button_press_time:
            duration = now - button_press_time[key]
            del button_press_time[key]

            if duration >= LONG_PRESS_DURATION and key <= NUM_SETS:
                if not set_switch_in_progress:
                    log(f"Long press → Set {key}")
                    set_switch_in_progress = True
                    with device_lock:
                        for dev in streamdocks:
                            dev.set_brightness(flash_brightness)
                    current_set = key - 1
                    apply_set(current_set)
                return

            if key in BUTTON_COMMANDS:
                log(f"Button {key} pressed")
                for cmd in BUTTON_COMMANDS[key][0]:
                    subprocess.Popen(cmd, start_new_session=True)

        elif key == DECK_ROTARY_CW:
            if not set_switch_in_progress:
                set_switch_in_progress = True
                with device_lock:
                    for dev in streamdocks:
                        dev.set_brightness(flash_brightness)
                current_set = (current_set + 1) % NUM_SETS
                log(f"Rotary → Set {current_set + 1}")
                apply_set(current_set)
        elif key == DECK_ROTARY_CCW:
            if not set_switch_in_progress:
                set_switch_in_progress = True
                with device_lock:
                    for dev in streamdocks:
                        dev.set_brightness(flash_brightness)
                current_set = (current_set - 1) % NUM_SETS
                log(f"Rotary → Set {current_set + 1}")
                apply_set(current_set)

# ==================== MAIN ====================
if __name__ == "__main__":
    print(f"MiraBox Controller v{__version__} starting...")

    for i in range(1, NUM_SETS + 1):
        sets[i-1] = load_set(i)

    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    sys.stdout = SilentCapture()
    start_http_api()

    manager = DeviceManager()
    streamdocks = manager.enumerate()
    threading.Thread(target=manager.listen, daemon=True).start()
    log(f"Found {len(streamdocks)} device(s)")

    with device_lock:
        for dev in streamdocks:
            dev.open()
            dev.init()
            dev.set_brightness(original_brightness)
            if isinstance(dev, StreamDockN1):
                dev.switch_mode(0)
            threading.Thread(target=dev.whileread, daemon=True).start()

    if sets[0]:
        apply_set(0)

    log("Ready")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down")
        sys.exit(0)

