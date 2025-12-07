# Mirabox Mbox-N4 (StreamDock N1) controller for Linux

![Mirabox N1](https://github.com/OH1KK/mirabox/blob/main/img/kkdeck.jpg?raw=true)

Python-based controller for the Mirabox Mbox-N4 / StreamDock N1 device.

Supports:
- Button short-press executes configured commands
- Long-press on buttons 1–10 jumps directly to set 1–10
- Rotary buttons 2, 3 and 4 can be used in json
- Images for buttons (64x64 pixels, png)
- Background image per set (320x240 pixels, png). Gimp template included.
- Brightness flash feedback on actions
- 10 independent button sets
- Runs as user systemd service
- Support dynamic icon updates by receiving a new image from network

This code includes part of StreamDock-Device-SDK which is available https://github.com/MiraboxSpace/StreamDock-Device-SDK/

## Installation

### 1. Device access (udev rule)

```bash
sudo tee /etc/udev/rules.d/99-mirabox.rules <<EOF
# Mirabox Mbox-N4 / StreamDock N1
SUBSYSTEM=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
KERNEL=="hiddev*", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```
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

or with verbose
```bash
./mirabox.py --debug
```

### 4. Auto-start (systemd user service)

```bash
mkdir -p ~/.config/systemd/user

sudo tee ~/.config/systemd/user/mirabox.service <<EOF
[Unit]
Description=Mirabox Controller daemon
After=graphical-session.target pipewire.service pipewire-pulse.service
PartOf=graphical-session.target
Documentation=https://github.com/OH1KK/mirabox

[Service]
Type=simple
WorkingDirectory=%h/mirabox
ExecStart=/usr/bin/python3 %h/mirabox/mirabox.py --enable-networking
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=graphical-session.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now mirabox.service
```

If you don't need dynamic icon updates then remove --enable-networking from unit file.

Starting and stopping service manually

```bash￼
systemctl --user stop mirabox.service
systemctl --user start mirabox.service
```

View service logs:
```bash￼
journalctl --user -u mirabox.service -f
```


## Configuration

Button sets are defined in dynamic/button-sets/button-set-1.json through button-set-10.json.

Example entries
GUI command:
```json
"1": {
  "image": "/usr/share/icons/hicolor/scalable/apps/firefox.png",
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

Note! If you are using dynamic updates, make backup of your button sets. Dynamic update will overwrite updates into file.

## Dynamic icon updates

You can update icons by sending a new version using network. You must start daemon with --enable-networking paremeter, otherwise it does not listen for updates. There is no security implemented in updates, to think before enabling dynamic updates.

Dynamic icon updates also overwrites json files so make sure you have backups for accidents.

### How dynamic icon update works 

mirabox works as server. It listens tcp port 8333. And you can send a new icon using script. For example

```bash
#!/bin/bash
# Note! Daemon must be running with --enable-networking to accept updates from net.

set -euo pipefail
# Function to clean up temp file on exit (even on Ctrl+C or errors)
cleanup() {
    [[ -f "$tempfile" ]] && rm -f "$tempfile"
}
trap cleanup EXIT

tempfile=$(mktemp --suffix=.png)
while [ forever ]; do
        # Get uptime
        UPTIME=`cat /proc/uptime | cut -d \  -f 1 | cut -d \. -f 1`
        # Make 64x64 pixel png from it
        convert -background blue -fill white -gravity center -font "DejaVu-Sans" \
                -size 64x64 -pointsize 12 label:"Uptime\nseconds\n$UPTIME" $tempfile
        # Send image to miraboxd. Update set 9 image 2.
        curl -s -X POST -H "Content-Type: application/octet-stream" --data-binary @$tempfile http://127.0.0.1:8333/update/9/1 >/dev/null
        sleep 1
done
```

## Controls

| Action                  | Function                          |
|-------------------------|-----------------------------------|
| Rotate left rotary      | Next / previous set               |
| Short press button      | Execute command                   |
| Long press button 1–10  | Jump to set 1–10                  |
| Short flash             | Button acknowledged               |
| Long flash              | Set change in progress            |

## Key codes (for reference)

```
Keycode 1 = button 1, status: 1 = pressed, 0 released
Keycode 2 = button 2, status: 1 = pressed, 0 released
Keycode 3 = button 3, status: 1 = pressed, 0 released
Keycode 4 = button 4, status: 1 = pressed, 0 released
Keycode 5 = button 5, status: 1 = pressed, 0 released
Keycode 6 = button 6, status: 1 = pressed, 0 released
Keycode 7 = button 7, status: 1 = pressed, 0 released
Keycode 8 = button 8, status: 1 = pressed, 0 released
Keycode 9 = button 9, status: 1 = pressed, 0 released
Keycode 10 = button 10, status: 1 = pressed, 0 released
Keycode 56 = Swipe right
Keycode 57 = Swipe left
Keycode 64 = touchscreen above of rotary button 1
Keycode 65 = touchscreen above of rotary button 2
Keycode 66 = touchscreen above of rotary button 3
Keycode 67 = touchscreen above of rotary button 4
Keycode 160 = rotary button 1 counterclockwise
Keycode 161 = rotary button 1 clockwise
Keycode 80 = rotary button 2 counterclockwise
Keycode 81 = rotary button 2 clockwise
Keycode 144 = rotary button 3 counterclockwise
Keycode 145 = rotary button 3 clockwise
Keycode 112 = rotary button 4 counterclockwise
Keycode 113 = rotary button 4 clockwise
Keycode 55 = rotary button 1 push
Keycode 53 = rotary button 2 push
Keycode 51 = rotary button 3 push
Keycode 51 = rotary button 4 push
```

## Credits

Code is product of Grok AI.
Instructed by OH1KK
