# FOR TESTING IF GSTREAMER WORKS
# import gi
# gi.require_version('Gst', '1.0')
# from gi.repository import Gst

# Gst.init(None)

# print(Gst.version_string())

import argparse
import gi
import os
import socket
import subprocess
import sys
import time
import threading
from start_video_record import start_video_record
from take_screenshot import take_screenshot

gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import GLib, Gst, GstRtspServer

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def start_rtsp_server(rtsp_port, device, stream_name):
    server = GstRtspServer.RTSPServer.new()
    server.props.service = rtsp_port
    server.attach(None)

    factory = GstRtspServer.RTSPMediaFactory.new()
    # Define pipeline which will be created during connection (FOR RADXA)
    launch_str = f"( v4l2src device={device} ! image/jpeg,width=1280,height=800,framerate=120/1 ! jpegparse ! rtpjpegpay name=pay0 pt=26 )"
    # (FOR WINDOWS)
    #launch_str = f"( ksvideosrc device-index={device} ! image/jpeg,width=1280,height=800,framerate=120/1 ! jpegdec ! videoconvert ! x264enc ! h264parse ! rtph264pay name=pay0 pt=96 )"
    # pipeline string below WORKS
    #launch_str = f"( ksvideosrc device-index={device} ! image/jpeg,width=1280,height=800,framerate=120/1 ! jpegparse ! rtpjpegpay name=pay0 pt=26 )"

    factory.set_launch(launch_str)
    factory.set_shared(True)

    server.get_mount_points().add_factory("/" + stream_name, factory)
    print(f"Camera : {device} \nUnder: rtsp://{get_local_ip()}:{rtsp_port}/{stream_name}")

    return server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-port", type=int, default=1234, help="Starting port for RTSP servers")
    args = parser.parse_args()

    num_of_cam = 2
    camera_devices = ["/dev/video"+str(i) for i in range(num_of_cam*2) if i%2 == 0]
    cubesat_cam = {    
       's5': {
           'device': 's',
           'url': "rtsp://192.168.77.2:8554/cubesat_cam", # <--- REPLACE WITH ACTUAL CUBESAT RTSP ADDRESS, IDONT REMEMBER THE IP, PORT, AND STREAM NAME
           'name': "Cam CubeSat"
       }
    }
    # hold all active servers
    servers = {}
    # map commands to device informations
    cam_info = {}
    # hold active recording pipelines
    recording_pipelines = {}

    print("--- Starting GStreamer RTSP Servers ---")
    local_ip = get_local_ip()
    for i, device in enumerate(camera_devices):
       port = args.base_port + i
       stream_name = f"cam{i+1}"
       rtsp_url = f"rtsp://{local_ip}:{port}/{stream_name}"
        
       try:
           server = start_rtsp_server(str(port), device, stream_name)
           servers[stream_name] = server
           cam_info[f's{i+1}'] = {
               'device': device,
               'url': rtsp_url,
               'name': "Cam"+str(i+1)
           }
       except GLib.Error as e:
           # GStreamer will throw an error if a camera doesn't exist at an index.
           print(f"Could not start server for Camera {device}: {e}")
    
    for command_key, info in cubesat_cam.items():
       cam_info[command_key] = info

    print("---------------------------------------")

    if not servers:
        print("No active RTSP servers found. Exiting.")
        sys.exit(1)

    Gst.init(None)
    loop = GLib.MainLoop()
    
    try:
        for i in range(len(servers)):
            print(f"Type 's{i+1}' to take a screenshot from CAM{i+1}.")
        print(f"Type r to record on all cameras.")
        print(f"Type t to stop all camera recordings.")
        print("Type 'q' to quit.")
        
        # Start a thread for the main Glib loop to run in the background
        loop_thread = threading.Thread(target=loop.run, daemon=True)
        loop_thread.start()

        while True:
            command = input("Enter command: ").strip().lower()
            if command == 'q':
                break
            elif command.startswith('s') and command in cam_info:
                while True:
                    time.sleep(5)
                    info = cam_info[command]
                    output_dir = '~/Desktop/svarog_share/real_ground_station/img.jpg'
                    take_screenshot(info['url'], output_dir, info['name'])
            elif command == 'r':  # New command to start recording for all cameras
                if not recording_pipelines:
                    print("Starting recording for all active cameras...")
                    for stream_name, info in cam_info.items():
                        print(stream_name)
                        print(info)
                        pipeline = start_video_record(info['url'], f'{info["name"]}_videos', stream_name)
                        if pipeline:
                            recording_pipelines[stream_name] = pipeline
                else:
                    print("Recording is already in progress.")
            elif command == 't':  # New command to stop all recordings
                if recording_pipelines:
                    print("Stopping all active recordings...")
                    for stream_name, pipeline in recording_pipelines.items():
                        # Set the pipeline to the NULL state for a clean shutdown
                        pipeline.set_state(Gst.State.NULL)
                        print(f"Recording stopped for {stream_name}.")
                    recording_pipelines.clear()
                else:
                    print("No active recordings to stop.")
            else:
                print("Invalid command. Please use one of the available camera commands or 'q'.")
    
    except KeyboardInterrupt:
        print("\nExiting screenshot center...")
    
    finally:
        # --- Clean up and terminate the RTSP servers ---
        if recording_pipelines:
            print("Terminating remaining recording pipelines...")
            for pipeline in recording_pipelines.values():
                pipeline.set_state(Gst.State.NULL)
        print("\n--- Shutting down RTSP servers ---")
        loop.quit()
        print("Shutdown complete.")
        sys.exit(0)



