# Mirabox Mbox-N4 Stream Deck Controller for Linux (Ubuntu)

![Mirabox N1](https://github.com/OH1KK/mirabox/blob/main/photo.jpg?raw=true)

A **fully functional, open-source Stream Deck-style controller** for the **Mirabox Mbox-N4 (StreamDock N1)** on **Ubuntu 24.04 / 25.10** (Wayland + GNOME).

This is my personal, battle-tested setup — rock-solid, no crashes, with **10 full decks**, **long-press deck switching**, **visual feedback**, **programmable rotaries**, and **perfect background support**.

> This is **not** a generic driver — it's a complete, ready-to-run macro deck solution that beats most commercial alternatives.

**Features:**
- 10 fully independent button sets
- Long-press any button 1–10 → instantly jump to Set 1–10
- Big left rotary → next/prev set
- Short press → run any command (CLI or GUI)
- Visual brightness flash on every press (you **know** it registered)
- Long bright flash during set change
- 800×200 RGB background support (no more frozen images)
- Programmable rotary encoders (volume, brightness, etc.)
- Zero background corruption or race conditions
- Runs as user systemd service (starts on login)

## Hardware

- Mirabox Mbox-N4 / StreamDock N1 (real version, not cheap clone)
- USB connection
- Tested on Ubuntu 24.04 & 25.10 (Wayland/GNOME)

## Installation

### 1. Allow user access to the device

Create udev rule:

```bash
sudo nano /etc/udev/rules.d/99-mirabox.rules
