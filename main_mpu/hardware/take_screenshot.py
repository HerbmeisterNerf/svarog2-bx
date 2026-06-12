import subprocess
import sys
import os
import time

def take_screenshot(rtsp_url, output_folder, cam_num):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate a unique filename with a timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filepath = os.path.join(output_folder, f"image_{timestamp}.jpg")
    
    # The GStreamer command line pipeline as a single string
    command_str = (
        f"gst-launch-1.0 rtspsrc location={rtsp_url} latency=50 is-live=true !"
        f" rtpjpegdepay ! jpegparse ! avdec_mjpeg ! "
        f" videoconvert ! textoverlay text=\"`date +%Y-%m-%d\ %H:%M:%S`\" valignment=bottom halignment=left ! " #can remove if things go wrong
        f" textoverlay text=\"{cam_num}\" valignment=top halignment=left ! " #can remove if things go wrong, this is just a text overlay of cam name and timestamp
        f"jpegenc snapshot=true ! filesink location=\"{filepath}\""
    )



    print(f"Capturing frame from {rtsp_url} and saving to {filepath}...")
    
    try:
        subprocess.run(command_str, check=True, shell=True)
        print("Screenshot saved successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error capturing screenshot: {e}")
    except FileNotFoundError:
        print("Error: 'gst-launch-1.0' not found. Ensure GStreamer is in your PATH.")


if __name__ == "__main__":
    # Example address
    ip = "172.26.37.216"
    rtsp_url = f"rtsp://{ip}:1234/cam1"

    # Define the output folder
    output_dir = "cam1_screenshots"

    take_screenshot(rtsp_url, output_dir)
