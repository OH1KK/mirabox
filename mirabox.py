#!/usr/bin/python3
import signal, sys, os, json, time, subprocess, threading
from StreamDock.DeviceManager import DeviceManager
from StreamDock.Devices.StreamDockN1 import StreamDockN1

NUM_SETS = 10                                 # 10 sets
current_set = 0
sets = []
streamdocks = []
set_switch_in_progress = False
original_brightness = 10
flash_brightness = 75

DECK_ROTARY_CCW = 160
DECK_ROTARY_CW  = 161
PROGRAMMABLE_ROTARIES = {80, 81, 144, 145, 112, 113}

# === LONG PRESS SUPPORT ===
LONG_PRESS_DURATION = 1.0
button_press_time = {}

# ----------------------------------------------------------------------
# (load_set, apply_set, flash_confirm, signal_handler, parse_feedback unchanged)
# ----------------------------------------------------------------------
# ... keep your existing load_set, apply_set, flash_confirm, signal_handler, parse_feedback ...

def load_set(n):
    try:
        with open(f"button-set-{n}.json") as f:
            data = json.load(f)
        bg = data.get("background", "./img/default-slider.png")
        buttons = data.get("buttons", {})
        normalized = {}
        for k, v in buttons.items():
            normalized[int(k)] = {
                "image": v.get("image"),
                "command": v.get("command", []),
                "gui": v.get("gui", False)
            }
        return {"bg": bg, "buttons": normalized}
    except Exception as e:
        print(f"Warning: set {n} failed: {e}")
        return None

def apply_set(idx):
    global BUTTON_COMMANDS, set_switch_in_progress, original_brightness
    s = sets[idx]
    if not s: return

    BUTTON_COMMANDS = {}
    for k, btn in s["buttons"].items():
        cmd = btn.get("command", [])
        if isinstance(cmd, list) and cmd and not isinstance(cmd[0], list):
            cmd = [cmd]
        BUTTON_COMMANDS[k] = (cmd, btn.get("gui", False))

    for dev in streamdocks:
        dev.set_touchscreen_image(s["bg"])
        dev.refresh()
        time.sleep(1.8)
        for i in range(1, 11):
            path = s["buttons"].get(i, {}).get("image", "./img/default-button.png")
            if not os.path.exists(path):
                path = "./img/default-button.png"
            dev.set_key_image(i, path)
            dev.refresh()
        time.sleep(0.12)

    print(f"Applied set {idx + 1}")

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

def parse_feedback(t):
    try:
        parts = t.split(", ")
        key = int(parts[2].split(": ")[1])
        status = int(parts[3].split(": ")[1])
        return key, status
    except: return None, None

# ----------------------------------------------------------------------
# ONLY THIS CLASS WAS WRONG – fixed with proper globals
# ----------------------------------------------------------------------
class StreamDockPrintCapture:
    def __init__(self):
        self.original_stdout = sys.stdout
        self.last_press_time = {}
        self.debounce = 0.05

    def write(self, text):
        self.original_stdout.write(text)
        t = text.strip()
        if t.startswith("Acknowledgement: ACK"):
            key, status = parse_feedback(t)
            if key is None:
                return

            now = time.time()
            global current_set, set_switch_in_progress, flash_brightness   # ← FIXED!

            # ---- BUTTON PRESS (status 1) ----
            if status == 1 and 1 <= key <= 10:
                if now - self.last_press_time.get(key, 0) > self.debounce:
                    self.last_press_time[key] = now
                    button_press_time[key] = now
                    flash_confirm()

            # ---- BUTTON RELEASE (status 0) ----
            elif status == 0 and key in button_press_time:
                press_duration = now - button_press_time[key]
                del button_press_time[key]

                if now - self.last_press_time.get(key, 0) > self.debounce:
                    self.last_press_time[key] = now

                    # LONG PRESS → jump to set N
                    if press_duration >= LONG_PRESS_DURATION and 1 <= key <= NUM_SETS:
                        if not set_switch_in_progress:
                            print(f"LONG PRESS button {key} ({press_duration:.2f}s) → Set {key}")
                            set_switch_in_progress = True
                            for dev in streamdocks:
                                dev.set_brightness(flash_brightness)
                            current_set = key - 1
                            apply_set(current_set)
                        return

                    # SHORT PRESS → normal command
                    self.handle_event(key)

            # ---- ROTARY & HOME (unchanged) ----
            elif key == DECK_ROTARY_CCW:
                self.handle_deck_rotary(-1); return
            elif key == DECK_ROTARY_CW:
                self.handle_deck_rotary(+1); return
            elif key == 55 and status == 1:
                self.handle_home(); return

            # Programmable rotaries
            elif key in PROGRAMMABLE_ROTARIES and status == 0:
                if now - self.last_press_time.get(key, 0) > self.debounce:
                    self.last_press_time[key] = now
                    self.handle_event(key)

        if t.endswith(("Status: 0", "Status: 1")):
            self.original_stdout.write("\n")

    def flush(self): self.original_stdout.flush()

    # ------------------------------------------------------------------
    # helper methods (unchanged)
    # ------------------------------------------------------------------
    def handle_deck_rotary(self, direction):
        global current_set, set_switch_in_progress, flash_brightness
        if set_switch_in_progress:
            return
        set_switch_in_progress = True
        for dev in streamdocks:
            dev.set_brightness(flash_brightness)
        current_set = (current_set + direction) % NUM_SETS
        apply_set(current_set)
        print(f"Deck Rotary → Set {current_set + 1}")

    def handle_home(self):
        global current_set, set_switch_in_progress, flash_brightness
        if set_switch_in_progress:
            return
        set_switch_in_progress = True
        for dev in streamdocks:
            dev.set_brightness(flash_brightness)
        current_set = 0
        apply_set(current_set)
        print("Home → Set 1")

    def handle_event(self, key):
        flash_confirm()
        if key in BUTTON_COMMANDS:
            cmds, gui = BUTTON_COMMANDS[key]
            print(f"Executing key {key} ({'GUI' if gui else 'CLI'})")
            for cmd in cmds:
                if not cmd: continue
                if gui:
                    subprocess.Popen(cmd, start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                else:
                    try:
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             env=os.environ.copy(), start_new_session=True)
                        running_processes[key] = p
                        out, err = p.communicate(timeout=5)
                        out, err = out.decode().strip(), err.decode().strip()
                        print(f"Success: {out}" if p.returncode == 0 else f"Failed: {err}")
                        running_processes.pop(key, None)
                    except Exception as e:
                        print(f"Error: {e}")

# ----------------------------------------------------------------------
# main – unchanged
# ----------------------------------------------------------------------
if __name__ == "__main__":
    for i in range(NUM_SETS):
        sets.append(load_set(i+1))

    signal.signal(signal.SIGINT, signal_handler)
    sys.stdout = StreamDockPrintCapture()

    manager = DeviceManager()
    streamdocks = manager.enumerate()
    threading.Thread(target=manager.listen, daemon=True).start()
    print(f"Found {len(streamdocks)} device(s)")

    for dev in streamdocks:
        dev.open(); dev.init(); dev.set_brightness(original_brightness)
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

