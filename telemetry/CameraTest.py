import time
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from gpiozero import Button, LED

picam2 = Picamera2()
input2 = Button(2)
output17 = LED(17)
output27 = LED(27)

video_config = picam2.create_video_configuration()
picam2.configure(video_config)
encoder = H264Encoder()

def start_recording():
    picam2.start_recording(encoder, create_file_name())
    print("start recording")
    
def create_file_name():
    #creates a variable with the time since the epoch with .h264 on the end
    #to save the video with that name
    file_name = str(time.time()) + ".h264"
    return file_name

def end_recording():
    output27(True)
    picam2.stop_recording()
    print("stop recording")
    output27(False)
    
#ouput 17 is for if camera is on or off
def output17(looped):
    if looped == True:
        output17.on()
    else:
        output17.off()
        
def output27(saving):
    if saving:
        output27.on()
    else saving:
        output27.off()
    
    
while True:
    print("again")
    looped = False
    output17(looped)
    print(time.time())
    
    #when gpio2 pin is connected to ground
    while input2.is_pressed():
        #starts recording
        if looped == False:
            looped = True
            output17(looped)
            start_recording()
        
        time.sleep(10)
        print("high")
    
    output17(looped)
    if looped == True:
        end_recording()
    time.sleep(10)

