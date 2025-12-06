#!/usr/bin/python3

import signal, sys, os, json, time, subprocess, threading, argparse
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL.Image")

from StreamDock.DeviceManager import DeviceManager
from StreamDock.Devices.StreamDockN1 import StreamDockN1

# ==================== ARGS ====================
__version__ = "0.1.0"
parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version=f"MiraBox Controller v{__version__}")
parser.add_argument("--debug", action="store_true", help="Show all messages (otherwise completely silent)")
args = parser.parse_args()
DEBUG = args.debug

def log(*msg):
    if DEBUG:
        print(*msg)

# ==================== CONFIG ====================
NUM_SETS = 10
current_set = 0
sets = [None] * NUM_SETS
streamdocks = []
set_switch_in_progress = False
original_brightness = 10
flash_brightness = 75

DECK_ROTARY_CCW = 160
DECK_ROTARY_CW  = 161
PROGRAMMABLE_ROTARIES = {80, 81, 144, 145, 112, 113}

LONG_PRESS_DURATION = 1.0
button_press_time = {}
running_processes = {}
BUTTON_COMMANDS = {}

# ==================== LOAD SET ====================
def load_set(n):
    fn = f"button-set-{n}.json"
    log(f"Loading {fn}")
    try:
        with open(fn) as f:
            data = json.load(f)
        bg = data.get("background", "./img/default-slider.png")
        buttons = {}
        for k, v in data.get("buttons", {}).items():
            key = int(k)
            img = v.get("image", "./img/default-button.png")
            buttons[key] = {"image": img, "command": v.get("command", []), "gui": v.get("gui", False)}
        log(f"{fn} → OK")
        return {"bg": bg, "buttons": buttons}
    except Exception as e:
        log(f"{fn} → FAILED: {e}")
        return None

# ==================== APPLY SET (silent) ====================
def apply_set(idx):
    global BUTTON_COMMANDS, set_switch_in_progress
    if not sets[idx]:
        set_switch_in_progress = False
        return

    s = sets[idx]
    BUTTON_COMMANDS = {}
    for k, btn in s["buttons"].items():
        cmd = btn.get("command", [])
        if isinstance(cmd, list) and cmd and not isinstance(cmd[0], list):
            cmd = [cmd]
        BUTTON_COMMANDS[k] = (cmd, btn.get("gui", False))

    for dev in streamdocks:
        bg = s["bg"] if os.path.exists(s["bg"]) else "./img/default-slider.png"
        dev.set_touchscreen_image(bg)
        dev.refresh()
        time.sleep(1.8)
        for i in range(1, 11):
            path = s["buttons"].get(i, {}).get("image", "./img/default-button.png")
            if not os.path.exists(path):
                path = "./img/default-button.png"
            dev.set_key_image(i, path)
            dev.refresh()
        time.sleep(0.12)

    log(f"→ Set {idx + 1}")
    for dev in streamdocks:
        dev.set_brightness(original_brightness)
    set_switch_in_progress = False

def flash_confirm():
    for dev in streamdocks:
        dev.set_brightness(flash_brightness)
    time.sleep(0.08)
    for dev in streamdocks:
        dev.set_brightness(original_brightness)

def signal_handler(sig, frame):
    if DEBUG:
        print("\nShutting down...")
    for p in list(running_processes.values()):
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=2)
            except subprocess.TimeoutExpired: p.kill()
    for d in streamdocks:
        try: d.close()
        except: pass
    sys.exit(0)

# ==================== COMPLETELY SILENT CAPTURE ====================
class SilentCapture:
    def __init__(self):
        self.original = sys.stdout
        self.last_press_time = {}
        self.debounce = 0.05

    def write(self, text):
        line = text.rstrip("\n")

        # Always process events
        if "Acknowledgement: ACK" in line:
            try:
                parts = line.split(", ")
                key = int(parts[2].split(": ")[1])
                status = int(parts[3].split(": ")[1])
                self._handle(key, status)
            except:
                pass

        # In normal mode → suppress everything
        if not DEBUG:
            return

        # Debug mode → print raw output
        self.original.write(text)

    def flush(self): self.original.flush()

    def _handle(self, key, status):
        now = time.time()
        global current_set, set_switch_in_progress

        # Button down
        if status == 1 and 1 <= key <= 10:
            if now - self.last_press_time.get(key, 0) > self.debounce:
                self.last_press_time[key] = now
                button_press_time[key] = now
                flash_confirm()

        # Button up
        elif status == 0 and key in button_press_time:
            duration = now - button_press_time[key]
            del button_press_time[key]
            if now - self.last_press_time.get(key, 0) > self.debounce:
                self.last_press_time[key] = now

                if duration >= LONG_PRESS_DURATION and key <= NUM_SETS:
                    if not set_switch_in_progress:
                        log(f"→ Set {key} (long press)")
                        set_switch_in_progress = True
                        for dev in streamdocks: dev.set_brightness(flash_brightness)
                        current_set = key - 1
                        apply_set(current_set)
                    return

                self._run(key)

        # Rotary
        elif key == DECK_ROTARY_CCW:
            self._rotary(-1)
        elif key == DECK_ROTARY_CW:
            self._rotary(+1)

        # Home
        elif key == 55 and status == 1:
            self._home()

        # Programmable rotaries
        elif key in PROGRAMMABLE_ROTARIES and status == 0:
            if now - self.last_press_time.get(key, 0) > self.debounce:
                self.last_press_time[key] = now
                self._run(key)

    def _rotary(self, d):
        global current_set, set_switch_in_progress
        if set_switch_in_progress: return
        set_switch_in_progress = True
        for dev in streamdocks: dev.set_brightness(flash_brightness)
        current_set = (current_set + d) % NUM_SETS
        log(f"→ Set {current_set + 1} (rotary)")
        apply_set(current_set)

    def _home(self):
        global current_set, set_switch_in_progress
        if set_switch_in_progress: return
        set_switch_in_progress = True
        for dev in streamdocks: dev.set_brightness(flash_brightness)
        current_set = 0
        log("→ Set 1 (home)")
        apply_set(current_set)

    def _run(self, key):
        flash_confirm()
        if key not in BUTTON_COMMANDS: return
        cmds, gui = BUTTON_COMMANDS[key]
        mode = "GUI" if gui else "CLI"
        log(f"Executing key {key} ({mode})")
        for cmd in cmds:
            if not cmd: continue
            try:
                if gui:
                    subprocess.Popen(cmd, start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         env=os.environ.copy(), start_new_session=True)
                    running_processes[key] = p
                    out, err = p.communicate(timeout=10)
                    out, err = out.decode().strip(), err.decode().strip()
                    if p.returncode == 0 and out:
                        log(f"Success: {out}")
                    elif p.returncode != 0:
                        log(f"Failed: {err or p.returncode}")
                    running_processes.pop(key, None)
            except Exception as e:
                log(f"Error: {e}")

# ==================== MAIN ====================
if __name__ == "__main__":
    if DEBUG:
        print(f"MiraBox Controller v{__version__} starting in DEBUG mode...")

    for i in range(NUM_SETS):
        sets[i] = load_set(i+1)

    signal.signal(signal.SIGINT, signal_handler)
    sys.stdout = SilentCapture()

    manager = DeviceManager()
    streamdocks = manager.enumerate()
    threading.Thread(target=manager.listen, daemon=True).start()
    log(f"Found {len(streamdocks)} device(s)")

    for dev in streamdocks:
        dev.open()
        dev.init()
        dev.set_brightness(original_brightness)
        if isinstance(dev, StreamDockN1):
            dev.switch_mode(0)
        threading.Thread(target=dev.whileread, daemon=True).start()

    if sets[0]:
        apply_set(0)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
