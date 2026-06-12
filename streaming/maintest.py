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

continuous_tasks = {}

def all_screenshot_task(all_cams_info, event):
    """
    Thread target function to take screenshots from ALL cameras at a fixed interval.
    """
    print(f"\n--- CONTINUOUS SCREENSHOT STARTED for ALL CAMERAS ---")
    interval = 10 # 10 seconds interval

    # Loop continues only while the Event is set
    while event.is_set(): 
        start_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] --- Starting Simultaneous Capture ---")
        
        # Launch a separate thread for EACH camera capture to happen concurrently
        capture_threads = []
        for command_key, info in all_cams_info.items():
            output_dir = os.path.join(os.getcwd(), f"{info['name'].replace(' ', '_')}_images")
            
            t = threading.Thread(
                target=take_screenshot,
                args=(info['url'], output_dir, info['name']),
                daemon=True # Mark as daemon so it won't block shutdown
            )
            capture_threads.append(t)
            t.start()
            
        # Wait for all capture threads to finish before starting the interval timer
        for t in capture_threads:
            t.join() 
            
        end_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] --- Simultaneous Capture Complete ({len(all_cams_info)} images saved) ---")
        
        # Calculate time elapsed and sleep for the remainder of the 10-second interval
        time_elapsed = end_time - start_time
        #time_to_sleep = max(0, interval - time_elapsed)
        time_to_sleep = interval

        if time_to_sleep > 0:
            time.sleep(time_to_sleep)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-port", type=int, default=1234, help="Starting port for RTSP servers")
    args = parser.parse_args()

    num_of_cam = 5
    camera_devices = ["/dev/video"+str(i) for i in range(num_of_cam*2) if i%2 == 0]
    #cubesat_cam = {    
    #    's5': {
    #        'device': 's',
    #        'url': "rtsp://192.168.77.2:8554/cubesat_cam", # <--- REPLACE WITH ACTUAL CUBESAT RTSP ADDRESS, IDONT REMEMBER THE IP, PORT, AND STREAM NAME
    #        'name': "Cam CubeSat"
    #    }
    #}
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
    
    #for command_key, info in cubesat_cam.items():
    #    cam_info[command_key] = info

    print("---------------------------------------")

    if not servers:
        print("No active RTSP servers found. Exiting.")
        sys.exit(1)

    Gst.init(None)
    loop = GLib.MainLoop()
    
    try:
        print(f"Type c to start snapshotting on all cameras.")
        print(f"Type a to stop snapshotting on all cameras. ")
        print(f"Type r to record on all cameras.")
        print(f"Type t to stop all camera recordings.")
        print("Type 'q' to quit.")
        
        # Start a thread for the main Glib loop to run in the background
        loop_thread = threading.Thread(target=loop.run, daemon=True)
        loop_thread.start()

        while True:
            flag = True
            command = input("Enter command: ").strip().lower()
            if command == 'q':
                break
            elif command == 'c':
                unified_key = 'all_cams'
                if unified_key in continuous_tasks and continuous_tasks[unified_key].is_set():
                    print("Continuous screenshot for all cameras is ALREADY running.")
                    continue

                # Create and set the control Event
                event = threading.Event()
                event.set()
                continuous_tasks[unified_key] = event

                # Launch the unified task in a new background thread
                threading.Thread(
                    target=all_screenshot_task,
                    args=(cam_info, event), # Pass the entire cam_info dict
                    daemon=True
                ).start()
            elif command == 'r':  # New command to start recording for all cameras
                if not recording_pipelines:
                    print("Starting recording for all active cameras...")
                    for stream_name, info in cam_info.items():
                        pipeline = start_video_record(info['url'], f'{info["name"]}_videos', stream_name)
                        if pipeline:
                            recording_pipelines[stream_name] = pipeline
                else:
                    print("Recording is already in progress.")
            elif command == 'a':
                # STOP ALL CONTINUOUS SCREENSHOTS
                if continuous_tasks:
                    print("Stopping all continuous screenshot tasks...")
                    for cmd, event in continuous_tasks.items():
                        event.clear() # Set the flag to False (STOP)
                    continuous_tasks.clear()
                else:
                    print("No continuous screenshot tasks are running.")
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

