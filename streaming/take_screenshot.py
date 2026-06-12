import subprocess
import sys
import shutil
import os
import time

def take_screenshot(rtsp_url, output_folder, cam_num):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate a unique filename with a timestamp
    timestamp = time.strftime("%d_%H_%M_%S")
    filepath = os.path.join(output_folder, f"{timestamp}{cam_num}.jpg")
    
    # The GStreamer command line pipeline as a single string
    command_str = (
        f"gst-launch-1.0 -q rtspsrc location={rtsp_url} latency=50 is-live=true !"
        f" rtpjpegdepay ! jpegparse ! avdec_mjpeg ! "
        f" videoconvert ! textoverlay text=\"`date +%Y-%m-%d\ %H:%M:%S`\" valignment=bottom halignment=left ! " #can remove if things go wrong
        f" textoverlay text=\"{cam_num}\" valignment=top halignment=left ! " #can remove if things go wrong, this is just a text overlay of cam name and timestamp
        f"jpegenc snapshot=true ! filesink location=\"{filepath}\""
    )



    print(f"Capturing frame from {rtsp_url} and saving to {filepath}...")
    
    try:
        subprocess.run(command_str, check=True, shell=True)
        print("Screenshot saved successfully.")
        duplicate_path = os.path.join(output_folder, f"realtime{cam_num}.jpg")
        duplicate_and_rename_image(filepath, duplicate_path)
        print("Duplicate successful!")
    except subprocess.CalledProcessError as e:
        print(f"Error capturing screenshot: {e}")
    except FileNotFoundError:
        print("Error: 'gst-launch-1.0' not found. Ensure GStreamer is in your PATH.")

def duplicate_and_rename_image(source_path, destination_path):
    """
    Duplicates a file and renames it.

    Args:
        source_path (str): The full path to the original file.
        destination_path (str): The full path for the new file, including the new name.
    """
    try:
        # Check if the source file exists
        if not os.path.exists(source_path):
            print(f"Error: The source file {source_path} does not exist.")
            return

        # Ensure the destination directory exists
        dest_dir = os.path.dirname(destination_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            print(f"Created directory: {dest_dir}")

        # Copy the file with a new name
        shutil.copy2(source_path, destination_path)
        print(f"File successfully duplicated from {source_path} to {destination_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Example address
    ip = "172.26.37.216"
    rtsp_url = f"rtsp://{ip}:1234/cam1"

    # Define the output folder
    output_dir = "cam1_screenshots"

    take_screenshot(rtsp_url, output_dir)

