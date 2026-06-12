# streaming

GStreamer RTSP server for multi-camera streaming from the Radxa Rock 3B.

## Running

```bash
python main.py --base-port 1234
```

Cameras are auto-detected at `/dev/video0`, `/dev/video2`, `/dev/video4`, ... (every even index).
Each camera gets its own RTSP stream at `rtsp://<radxa-ip>:<base-port+n>/cam<n+1>`.

## Commands (interactive)

| Command | Action |
|---------|--------|
| `s1`, `s2`, ... | Continuous screenshot loop for that camera |
| `r` | Start recording all cameras |
| `t` | Stop all recordings |
| `q` | Quit |

## Files

| File | Role |
|------|------|
| `main.py` | RTSP server entry point, interactive command loop |
| `maintest.py` | Simpler test/development version |
| `start_video_record.py` | Starts a GStreamer recording pipeline for a given RTSP URL |
| `take_screenshot.py` | Captures a JPEG snapshot from an RTSP stream via GStreamer |

## Dependencies

```
gstreamer1.0-plugins-good
gstreamer1.0-rtsp-server
python3-gi
python3-gst-1.0
```
