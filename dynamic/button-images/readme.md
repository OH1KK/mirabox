This is location for dynamically updated (uploaded) button images

Exaple updating script

```bash
#!/bin/bash

# Note! Daemon must be running with --enable-networking to accept updates from net.

# Get uptime
UPTIME=`uptime | cut -d \, -f 1 | cut -d p -f 2`

# Make 64x64 pixel png from it
convert -background blue -fill white -gravity center -font "DejaVu-Sans" \
        -size 64x64 -pointsize 16 label:"uptime\n$UPTIME" ./uptime-button.png

# Send image to miraboxd. Update set 9 image 2.
curl -X POST -H "Content-Type: application/octet-stream" --data-binary @uptime-button.png http://127.0.0.1:8333/update/9/1
```
