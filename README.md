# Mirabox Mbox-N4-Stream-Deck

This is my try to to get Mirabox M4 Stream Deck to work in Ubuntu 24.10. Repository is mainly for myself to remember how I got it working. This is not production ready code, instead an example how to communicate with a device.

This code includes part of StreamDock-Device-SDK which is available https://github.com/MiraboxSpace/StreamDock-Device-SDK/

## Install

First make mirabox available to regular user

Make file /etc/udev/rules.d/99-mirabox.rules and add there
````
# Allow user access to Mirabox USB HID and Bulk device
SUBSYSTEM=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
KERNEL=="hiddev*", ATTRS{idVendor}=="6603", ATTRS{idProduct}=="1007", MODE="0666", TAG+="uaccess"
````
Then reload rules

````
sudo udevadm control --reload-rules
sudo udevadm trigger
````
Then unplug mirabox and plug it again.

Install some depencies

````
sudo apt install -y python3-pyudev libusb-dev libhidapi-libusb0 python3-willow git
````

Then clone this repository and try it out.

````
git clone https://github.com/OH1KK/mirabox
cd mirabox
chmod +x kkdeck.py
````
## After install

Troubleshoot.

## Usage

Rotary button 1 in reserved for swithcig sets. Rotate clockwise or counter clokcwise. Also pushing rotary button selects set 1. 

Alterate switch: A long press for button 1-10 selects set 1-10.

Short button press executes command in json.

Long press button 1-10 selects button sets 1-10

Button sets are in files named button-set-1.json - button-set-10.json

To execute script without gui

````
"112": {
      "image": "./img/volume-down.png",
      "command": ["/home/oh1kk/koodi/gqrx-remote/gqrx-remote.py", "volumedown"]
    },
````

To execute script with gui

````
  "buttons": {
    "1": {
      "image": "/usr/share/icons/hicolor/64x64/apps/firefox.png",
      "command": ["firefox", "https://x.com/i/grok"],
      "gui": true
    },
````

Execute multiple commands in single push

````
    "2": {
      "image": "./img/yle1.png",
      "command": [["/home/oh1kk/koodi/gqrx-remote/gqrx-remote.py", "F", "91400000"],
                 ["/home/oh1kk/koodi/gqrx-remote/gqrx-remote.py", "M", "WFM"]]
    },
````

## Key codes

````
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
Keycode 64 = touchscreen above of button 1
Keycode 65 = touchscreen above of button 1
Keycode 66 = touchscreen above of button 1
Keycode 67 = touchscreen above of button 1
Keycode 160 = button 1 counterclockwise
Keycode 161 = button 1 clockwise
Keycode 80 = button 2 counterclockwise
Keycode 81 = button 2 clockwise
Keycode 144 = button 3 counterclockwise
Keycode 145 = button 3 clockwise
Keycode 112 = button 4 counterclockwise
Keycode 113 = button 4 clockwise
Keycode 55 = button 1 push
Keycode 53 = button 2 push
Keycode 51 = button 3 push
Keycode 51 = button 4 push
````
