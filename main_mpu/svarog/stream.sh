#!/bin/bash

# Check if a port number was provided
if [ -z "$1" ]; then
    echo "Error: Please provide a port number."
    echo "Usage: $0 <port_number>"
    exit 1
fi

PORT=$1
LOCATION="rtsp://172.16.18.191:${PORT}/cam"

echo "Starting stream from: ${LOCATION}"

# Run the GStreamer pipeline
gst-launch-1.0 -v \
    rtspsrc latency=0 protocols=tcp buffer-mode=none drop-on-latency=true location="$LOCATION" ! \
    rtpjpegdepay ! \
    jpegparse ! \
    avdec_mjpeg ! \
    queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! \
    videoconvert ! \
    autovideosink sync=false
