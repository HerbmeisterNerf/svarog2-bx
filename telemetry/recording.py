import time
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
import argparse

#command
#python recording.py --length=30 --fps=60
#records 30 second video at 60fps 

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration())

def record(length, fps):
    encoder = H264Encoder(framerate = fps, enable_sps_framerate=True)
    
    picam2.start_recording(encoder, create_file_name())
    print("recording started")
    time.sleep(length)
    picam2.stop_recording()
    print("recording finished")
    
def create_file_name():
    #creates a variable with the date and time
    #to save the video with that name
    file_name = str(time.strftime("%c")) + ".h264"
    return file_name


parser = argparse.ArgumentParser(description="Records video of known length and framerate as a .h264 file")
parser.add_argument("--length", required = True, type=int)
parser.add_argument("--fps", required = True, type=int)
args = parser.parse_args()
length = args.length
fps = args.fps

record(length, fps)
