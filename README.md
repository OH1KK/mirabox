# Mirabox Mbox-N4 (StreamDock N1) controller for Linux

Python-based controller for the Mirabox Mbox-N4 / StreamDock N1 device on Ubuntu 24.04 / 25.10 (Wayland + GNOME).

Supports:
- 10 independent button sets
- Long-press on buttons 1–10 jumps directly to set 1–10
- Short-press executes configured commands
- Left large rotary switches sets forward/backward
- Background image per set (320x240 RGB)
- Brightness flash feedback on actions
- Programmable rotary encoders
- Runs as user systemd service

## Installation

### 1. Device access (udev rule)

```bash
sudo tee /etc/udev/rules.d/99-mirabox.rules <<EOF
# Mirabox Mbox-N4 / StreamDock N1
SUBSYSTEM=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
KERNEL=="hiddev*", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
EOF
```

sudo udevadm control --reload-rules && sudo udevadm trigger

Unplug and replug the device after this step.

### 2. Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-pyudev libhidapi-libusb0 git
pip3 install --user pillow willow
```

### 3. Clone and test

```bash
git clone https://github.com/OH1KK/mirabox.git
cd mirabox
chmod +x mirabox.py
./mirabox.py
```

### 4. Auto-start (systemd user service)

```bash
mkdir -p ~/.config/systemd/user
cp mirabox.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mirabox.service
```
Modify mirabox.service to match your user.

View logs:
```bash￼
journalctl --user -u mirabox.service -f
```

## Configuration

Button sets are defined in files button-set-1.json through button-set-10.json.

Example entries
GUI command:
```json
"1": {
  "image": "/usr/share/icons/hicolor/scalable/apps/firefox.svg",
  "command": ["firefox", "https://example.com"],
  "gui": true
}
```

Multiple commands:
```json
"2": {
  "image": "./img/icon.png",
  "command": [
    ["command1", "arg"],
    ["command2", "arg"]
  ]
}
```

Rotary encoder example (volume):
```json
"81": { "image": "./img/vol-up.png",   "command": ["amixer", "set", "Master", "5%+"] },
"80": { "image": "./img/vol-down.png", "command": ["amixer", "set", "Master", "5%-"] }
```

### Controls

Action Function
Large left rotary > Next / previous set
Push large rotary (key 55)  > Jump to set 1
Short press button 1–10 > Execute command
Long press button 1–10 > Jump to corresponding set (1–10)
Short brightness flash > Button press acknowledged
Long brightness flash > Set change in progress

Key codes (for reference)

Buttons 1–10          → key 1–10
Large rotary CCW/CW   → 160 / 161
Small rotaries        → 80/81, 144/145, 112/113
Large rotary push     → key 55



