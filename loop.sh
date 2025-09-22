#!/bin/bash
for i in {1..300}; do
    echo "$i Messung"
    python3 usb-streaming-remote2.py >> output.log
    echo "---- DEBUG: letzte 10 Zeilen ----"
    tail -n 10 output.log
    sleep 10
done
