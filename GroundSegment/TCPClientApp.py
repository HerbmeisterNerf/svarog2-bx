############ standard libraries ############
import tkinter as tk
from PIL import Image, ImageTk
import pandas as pd
import queue
import time

############ custom libraries ############
from MessagePack import MessagePack
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from LiveUpdatesCamera import LiveUpdatesCamera
from CommonData import CommonData
from PortCommunication import PortCommunication
from RespondTCP import RespondTCP
from WatchTCP import WatchTCP
from WatchTelem import WatchTelem
from WatchCamera import WatchCamera

############ class ############
class TCPClientApp:
    '''
    This class contains the GUI for the TCP client
    '''

############ Initializer ############

    def __init__(self, master):

        # other variables
        CommonData.telemetryParameters = 35
        self.current_packet = MessagePack()

        self.master = master
        self.master.protocol("WM_DELETE_WINDOW",self.exitfunc)
        master.title("BX34 SVAROG GROUND SEGMENT")
        master.configure(bg='black')
        CommonData.TelemFreqVal = tk.DoubleVar()
        CommonData.ImgFreqVal = tk.DoubleVar()
        self.imgbaudrate = tk.DoubleVar()
        self.tableLabels = []

        ###### GUI Elements ######

        # Add logo
        #Main two frames
        self.left_panel = tk.Frame(master,width=300,height=500,bg="grey")
        self.left_panel.grid(row=0,column=0)
        self.left_panel.grid_propagate(False)
        self.right_panel = tk.Frame(master,width=600,height=500,bg="white")
        self.right_panel.grid(row=0,column=1)
        self.right_panel.grid_propagate(False)

        #Button containment frame

        self.left_button_panel = tk.Frame(self.left_panel,width=300,height=150)
        self.left_button_panel.grid_propagate(False)
        self.left_button_panel.grid(column=0,row=0,sticky=tk.N)

        self.left_data_panel = tk.Frame(self.left_panel,width=300,height=400)
        self.left_data_panel.grid(column=0,row=1,sticky="se")
        self.left_data_panel.grid_propagate(False)

        self.right_button_panel = tk.Frame(self.right_panel,width=600,height=130)
        self.right_button_panel.grid(column=0,row=0,sticky=tk.N)
        self.right_button_panel.grid_propagate(False)

        self.right_pic_panel = tk.Frame(self.right_panel,width=600,height=370)
        self.right_pic_panel.grid(column=0,row=1,sticky="se")
        self.right_pic_panel.pack_propagate(False)

        self.rates_panel = tk.Frame(self.right_button_panel,width=150,height=130)
        self.rates_panel.grid(column=0,row=0)
        self.rates_panel.pack_propagate(False)

        self.actions_panel = tk.Frame(self.right_button_panel,width=300,height=130)
        self.actions_panel.grid(column=1,row=0)
        self.actions_panel.grid_propagate(False)

        self.important_panel = tk.Frame(self.right_button_panel,width=150,height=130,bg="red")
        self.important_panel.grid(column=2,row=0)
        self.important_panel.pack_propagate(False)

        self.add_logo(self.left_button_panel)
        self.connect_button = tk.Button(self.left_button_panel, text="Connect to server",height=1,font=("Arial",8), command=self.connect_socket, bg='white', fg='black')
        self.connect_button.grid(row=1,column=0)

        self.disconnect_button = tk.Button(self.left_button_panel, text="Disconnect to server" ,height=1,font=("Arial",8),command=self.disconnect_socket,bg='white', fg='black', state=tk.DISABLED)
        self.disconnect_button.grid(row=1,column=1)

        self.telemFrequency = tk.Scale(self.rates_panel,from_=1.2, to=10, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=0.1,variable=CommonData.TelemFreqVal,label="Telemetry intervals (s)")
        self.telemFrequency.pack(side=tk.TOP,padx=10)

        self.telemetryButton = tk.Button(self.left_button_panel, text="Telemetry currently off",height=1,font=("Arial",8), command=self.toggleTelem, bg='red', fg='white', state=tk.DISABLED)
        self.telemetryButton.grid(row=2,column=0)

        self.imgFrequency = tk.Scale(self.rates_panel,from_=10, to=60, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=CommonData.ImgFreqVal,label="Image intervals (s)")
        self.imgFrequency.pack(side=tk.TOP,padx=10)

        self.imgrate = tk.Scale(self.rates_panel,from_=32, to=1638, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=self.imgbaudrate,label="Image bit rate (Kbit/s)")
        self.imgrate.pack(side=tk.TOP,padx=10)

        self.imageButton = tk.Button(self.left_button_panel, text="Camera currently off", height=1,font=("Arial",8),command=self.toggleCamera, bg='red', fg='white', state=tk.DISABLED)
        self.imageButton.grid(row=2,column=1)

        self.outputTelemetryButton = tk.Button(self.left_button_panel, text="Telemetry output currently off", height=1,font=("Arial",8),command=self.toggleOutputTelemetry, bg='red', fg='white', state=tk.DISABLED)
        self.outputTelemetryButton.grid(row=3,column=0)

        # Action buttons
        self.H1Button = tk.Button(self.actions_panel,text="Heater 1",font=("Arial",7),  command=self.actuateH1 ,state=tk.DISABLED)
        self.H1Button.grid(column=0,row=0,padx=4,pady=4)
        self.H2Button = tk.Button(self.actions_panel,text="Heater 2",font=("Arial",7),  command=self.actuateH2 ,state=tk.DISABLED)
        self.H2Button.grid(column=1,row=0,padx=2,pady=4)
        self.H3Button = tk.Button(self.actions_panel,text="Heater 3",font=("Arial",7),  command=self.actuateH3 ,state=tk.DISABLED)
        self.H3Button.grid(column=2,row=0,padx=2,pady=4)
        self.H4Button = tk.Button(self.actions_panel,text="Heater 4",font=("Arial",7),  command=self.actuateH4 ,state=tk.DISABLED)
        self.H4Button.grid(column=3,row=0,padx=2,pady=4)
        self.H5Button = tk.Button(self.actions_panel,text="Heater 5",font=("Arial",7),  command=self.actuateH5 ,state=tk.DISABLED)
        self.H5Button.grid(column=4,row=0,padx=2,pady=4)
        self.H6Button = tk.Button(self.actions_panel,text="Heater 6",font=("Arial",7),  command=self.actuateH6 ,state=tk.DISABLED)
        self.H6Button.grid(column=5,row=0,padx=2,pady=4)

        self.BW1Button = tk.Button(self.actions_panel,text="BW 1",font=("Arial",7),   command=self.actuateBW1 ,state=tk.DISABLED)
        self.BW1Button.grid(column=0,row=1,padx=2,pady=4)
        self.BW2Button = tk.Button(self.actions_panel,text="BW 2",font=("Arial",7),   command=self.actuateBW2 ,state=tk.DISABLED)
        self.BW2Button.grid(column=1,row=1,padx=2,pady=4)
        self.MOTButton = tk.Button(self.actions_panel,text="MOT EN",font=("Arial",7),  command=self.actuateMOT ,state=tk.DISABLED)
        self.MOTButton.grid(column=2,row=1,padx=2,pady=4)

        self.C1Button = tk.Button(self.actions_panel,text="C1 EN",font=("Arial",7),  command=self.actuateC1 ,state=tk.DISABLED)
        self.C1Button.grid(column=0,row=2,padx=2,pady=4)
        self.C2Button = tk.Button(self.actions_panel,text="C2 EN",font=("Arial",7),  command=self.actuateC2 ,state=tk.DISABLED)
        self.C2Button.grid(column=1,row=2,padx=2,pady=4)
        self.C3Button = tk.Button(self.actions_panel,text="C3 EN",font=("Arial",7),  command=self.actuateC3 ,state=tk.DISABLED)
        self.C3Button.grid(column=2,row=2,padx=2,pady=4)
        self.C4Button = tk.Button(self.actions_panel,text="C4 EN",font=("Arial",7),  command=self.actuateC4 ,state=tk.DISABLED)
        self.C4Button.grid(column=3,row=2,padx=2,pady=4)

        self.timestamp = tk.StringVar()
        self.timestamp.set('timestamp')
        self.imgtimestamp = tk.Label(self.right_pic_panel, textvariable = self.timestamp)
        self.imgtimestamp.pack()

        # # create list of data
        self.get_data_format()
        self.create_data_table()

        # # create image from camera
        self.add_image_camera(self.right_pic_panel,"logoPlaceholder.png")

        ###### Receive data ######
        # Start the thread
        self.start_live_updates()

############ Methods ############

    def exitfunc(self):
        if CommonData.runTelemetry or CommonData.runCamera:
            self.disconnect_socket()
        self.master.destroy()

    ###### making it look nice ######

    def add_logo(self, frame):
        original_image = Image.open('logo.png')
        resized_image = original_image.resize((150, 45), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(resized_image)

        self.logo_label = tk.Label(frame, image=self.logo)
        self.logo_label.grid(column=0,row=0)

    ###### live images ######

    def add_image_camera(self, frame, filename):
        img = ImageTk.PhotoImage(Image.open(filename).resize((600, 350), Image.Resampling.LANCZOS))
        self.panel = tk.Label(frame, image=img)
        self.panel.image = img
        self.panel.pack()

    ###### sockets ######

    def connect_socket(self):
        # Set up a TCP connection with the server
        PortCommunication.open_TCP()

        # Update server connection buttons
        self.connect_button.configure(bg="green",fg="white")
        self.connect_button.configure(state=tk.DISABLED)
        self.disconnect_button.configure(bg="red",fg="white")
        self.disconnect_button.configure(state=tk.NORMAL)

        self.H1Button.configure(state=tk.NORMAL)
        self.H2Button.configure(state=tk.NORMAL)
        self.H3Button.configure(state=tk.NORMAL)
        self.H4Button.configure(state=tk.NORMAL)
        self.H5Button.configure(state=tk.NORMAL)
        self.H6Button.configure(state=tk.NORMAL)
        self.BW1Button.configure(state=tk.NORMAL)
        self.BW2Button.configure(state=tk.NORMAL)
        self.MOTButton.configure(state=tk.NORMAL)
        self.C1Button.configure(state=tk.NORMAL)
        self.C2Button.configure(state=tk.NORMAL)
        self.C3Button.configure(state=tk.NORMAL)
        self.C4Button.configure(state=tk.NORMAL)

        # Update server request buttons
        self.telemetryButton.configure(state=tk.NORMAL)
        self.imageButton.configure(state=tk.NORMAL)
        # Update output buttons
        self.outputTelemetryButton.configure(state=tk.NORMAL)
        # Print connection status
        print("TCP client running...")
        print("Connecting to server at IP: ", CommonData.server_name, " PORT: ", CommonData.server_TCP_port)

    def disconnect_socket(self):
        # Update server connection buttons
        self.connect_button.configure(bg="white",fg="black")
        self.connect_button.configure(state=tk.NORMAL)
        self.disconnect_button.configure(bg="white",fg="black")
        self.disconnect_button.configure(state=tk.DISABLED)

        # Update server request buttons
        self.toggleOutputTelemetry(False)
        self.outputTelemetryButton.configure(state=tk.DISABLED)
        self.toggleTelem(False)
        self.telemetryButton.configure(state=tk.DISABLED)
        self.toggleCamera(False)
        self.imageButton.configure(state=tk.DISABLED)

        self.H1Button.configure(state=tk.DISABLED)
        self.H2Button.configure(state=tk.DISABLED)
        self.H3Button.configure(state=tk.DISABLED)
        self.H4Button.configure(state=tk.DISABLED)
        self.H5Button.configure(state=tk.DISABLED)
        self.H6Button.configure(state=tk.DISABLED)
        self.BW1Button.configure(state=tk.DISABLED)
        self.BW2Button.configure(state=tk.DISABLED)
        self.MOTButton.configure(state=tk.DISABLED)
        self.C1Button.configure(state=tk.DISABLED)
        self.C2Button.configure(state=tk.DISABLED)
        self.C3Button.configure(state=tk.DISABLED)
        self.C4Button.configure(state=tk.DISABLED)

        # Close the TCP connection
        PortCommunication.close_TCP()
        # Print connection status
        print("Closing Socket...")

    ###### telemetry ######

    def get_data_format(self):
        self.dataFormat = pd.read_csv('dataFormat.csv', header=None)
        for i in range(CommonData.telemetryParameters):
            for j in range(4):
                self.dataFormat.iloc[i, j+1] = float(self.dataFormat.iloc[i, j+1])

    def create_data_table(self):
        for i in range(CommonData.telemetryParameters):
            # add text
            label = tk.Label(self.left_data_panel, font=("Arial", 7))
            label.grid(row=(1+i%18), column=(2*(i//18)), padx=2, pady=2, columnspan=1)
            label.configure(text=self.dataFormat.iloc[i, 0])

            # prep and save data columns
            self.tableLabels.insert(i, tk.Label(self.left_data_panel, font=("Arial",7), fg='black'))
            self.tableLabels[i].grid(row=(1+i%18), column=(1+2*(i//18)), padx=2, pady=2, columnspan=1)

            # add data
            self.tableLabels[i].configure(text=0.0)

    ###### live updates ######

    def start_live_updates(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        try:
            WatchTCP().start()
            WatchTelem(self.current_packet,
                        self.dataFormat,
                        self.tableLabels).start()
            WatchCamera(self.right_pic_panel,
                        self.panel,
                        self.timestamp,
                        round(float(4096/self.imgbaudrate.get()*8/1000),3)).start()
        except Exception as e:
            print(f'An exception occurred in the live updates: {e}')

    ###### toggles ######

    def __toggleOff(self, button, name: str):
        '''
        Modifies a toggle button appearance to indicate that the feature is off
        '''

        button.config(text=name+ " currently off")
        button.config(bg="red", fg="white")

    def __toggleOn(self, button, name: str):
        '''
        Modifies a toggle button appearance to indicate that the feature is on
        '''

        button.config(text=name+ " currently on")
        button.config(bg="green", fg="white")

    def toggleTelem(self, flag=True):
        '''
        Switches the telemetry update on or off
        '''

        name = "Telemetry"
        if flag: # nominal behaviour
            if CommonData.runTelemetry:
                CommonData.runTelemetry = False
                self.__toggleOff(self.telemetryButton, name)
            else:
                CommonData.runTelemetry = True
                self.__toggleOn(self.telemetryButton, name)
        else: # forced shut down
            CommonData.runTelemetry = False
            self.__toggleOff(self.telemetryButton, name)
    
    def toggleCamera(self, flag=True):
        '''
        Switches the camera update on or off
        '''

        name = "Camera"
        if flag: # nominal behaviour
            if CommonData.runCamera:
                CommonData.runCamera = False
                self.__toggleOff(self.imageButton, name)
            else:
                CommonData.runCamera = True
                self.__toggleOn(self.imageButton, name)
        else: # forced shut down
            CommonData.runCamera = False
            self.__toggleOff(self.imageButton, name)

    def toggleOutputTelemetry(self, flag=True):
        '''
        Switches the output telemetry on or off
        '''

        name = "Telemetry output"
        if flag: # nominal behaviour
            if CommonData.outputTelemetry:
                CommonData.outputTelemetry = False
                self.__toggleOff(self.outputTelemetryButton, name)
            else:
                CommonData.outputTelemetry = True
                self.__toggleOn(self.outputTelemetryButton, name)
        else: # forced shut down
            CommonData.outputTelemetry = False
            self.__toggleOff(self.outputTelemetryButton, name)

    ###### actuators ######
    def actuateH1(self):
        pin = "start:H1end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateH2(self):
        pin = "start:H2end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateH3(self):
        pin = "start:H3end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateH4(self):
        pin = "start:H4end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateH5(self):
        pin = "start:H5end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateH6(self):
        pin = "start:H6end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateBW1(self):
        pin = "start:B1end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateBW2(self):
        pin = "start:B2end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateMOT(self):
        pin = "start:MOend:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateC1(self):
        pin = "start:C1end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateC2(self):
        pin = "start:C2end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateC3(self):
        pin = "start:C3end:"
        CommonData.client_TCP_socket.send(pin.encode())
    def actuateC4(self):
        pin = "start:C4end:"
        CommonData.client_TCP_socket.send(pin.encode())    

############ Main ############

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
