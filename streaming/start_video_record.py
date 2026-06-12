from gi.repository import GLib, Gst

import os
import time


def start_video_record(rtsp_url, output_dir, camera_name):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate a unique filename with a timestamp
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(output_dir, f"{camera_name}_{timestamp}.avi")
    # filepath = os.path.join(output_dir, f"{camera_name}_{timestamp}.mp4")

    print(f"Starting recording for {camera_name}...")
    print(f"Saving to: {filepath}")

    # Build the pipeline string
    # rtsp_url will be set as a property on the rtspsrc element

    pipeline_str = (
        f"rtspsrc location={rtsp_url} is-live=true ! "
        f"rtpjpegdepay ! jpegparse ! avimux ! filesink name=sink location={filepath}"
    )

    try:
        # Use Gst.parse_launch to create the pipeline from the string
        pipeline = Gst.parse_launch(pipeline_str)

        # Start the pipeline
        pipeline.set_state(Gst.State.PLAYING)

        return pipeline

    except GLib.GError as e:
        print(f"Error building pipeline for {camera_name}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
