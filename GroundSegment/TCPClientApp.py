############ standard libraries ############
import tkinter as tk
from PIL import Image, ImageTk
import pandas as pd
from tkinter import messagebox
from tkinter import ttk

############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication
from WatchTCP import WatchTCP
from WatchTelem import WatchTelem
from WatchCamera import WatchCamera
from WatchPing import WatchPing

############ class ############
class TCPClientApp:
    '''
    This class contains the GUI for the TCP client
    '''

############ Initializer ############

    def __init__(self, master):

        # other variables
        CommonData.telemetryParameters = 35

        self.master = master
        self.master.protocol("WM_DELETE_WINDOW",self.exitfunc)
        master.title("BX34 SVAROG GROUND SEGMENT")
        master.configure(bg='black')
        self.TelemFreqVal = tk.DoubleVar()
        self.ImgFreqVal = tk.DoubleVar()
        self.imgbaudrate = tk.DoubleVar()
        self.ActionButtons = tk.IntVar()
        self.ActionButtons = 0
        self.PisButtons = tk.IntVar()
        self.PisButtons = 0
        self.tableLabels = []

        ###### GUI Elements ######

        # Add logo
        #Main two frames
        self.left_panel = tk.Frame(master,width=300,height=600)
        self.left_panel.grid(row=0,column=0)
        self.left_panel.grid_propagate(False)
        self.right_panel = tk.Frame(master,width=600,height=600)
        self.right_panel.grid(row=0,column=1)
        self.right_panel.grid_propagate(False)
        self.right2_panel = tk.Frame(master,width=200,height=600)
        self.right2_panel.grid(row=0,column=2)
        self.right2_panel.grid_propagate(False)


        #Frames for testing and controlling RPIs

        self.rpi1testpanel = tk.Frame(self.right2_panel,width=194,height=80)
        self.rpi1testpanel.grid(row=0,column=1,pady=20,padx=3)
        self.rpi1testpanel.grid_propagate(False)
        #testo = tk.Label(self.rpi1testpanel,text="RPI1")
        #testo.grid(row=0,column=1)
        self.rpi1Stat = tk.StringVar
        self.rpi1Stat = "red"
        self.rpi1status = tk.Frame(self.rpi1testpanel,width=20,height=20,bg=self.rpi1Stat)
        self.rpi1status.grid(row=0,column=0,padx=2,pady=2)
        testo1 = tk.Label(self.rpi1testpanel,text="RPI1")
        testo1.grid(row=0,column=1)
        self.R1 = tk.Button(self.rpi1testpanel,text="Record",height=1,font=("Arial",8)) 
        self.R1.grid(row=1,column=1,padx=2,pady=2)
        self.S1 = tk.Button(self.rpi1testpanel,text="Status",height=1,font=("Arial",8)) 
        self.S1.grid(row=1,column=2,padx=2,pady=2)
        self.Check1 = tk.Button(self.rpi1testpanel,text="Check",height=1,font=("Arial",8),command=self.HealthC1) 
        self.Check1.grid(row=1,column=3,padx=2,pady=2)
        TR1 = tk.Label(self.rpi1testpanel,text="Recorded %",font=("Arial",8))
        TR1.grid(row=2,column=2,padx=2,pady=2)
        TW1 = tk.Label(self.rpi1testpanel,text="Written %",font=("Arial",8))
        TW1.grid(row=2,column=3,padx=2,pady=2)

#RPI 2
        self.rpi2testpanel = tk.Frame(self.right2_panel,width=194,height=80)
        self.rpi2testpanel.grid(row=1,column=1,pady=20,padx=3)
        self.rpi2testpanel.grid_propagate(False)
        #testo = tk.Label(self.rpi1testpanel,text="RPI1")
        #testo.grid(row=0,column=1)
        self.rpi2Stat = tk.StringVar
        self.rpi2Stat = "red"
        self.rpi2status = tk.Frame(self.rpi2testpanel,width=20,height=20,bg=self.rpi2Stat)
        self.rpi2status.grid(row=0,column=0,padx=2,pady=2)
        testo2 = tk.Label(self.rpi2testpanel,text="RPI2")
        testo2.grid(row=0,column=1)
        self.R2 = tk.Button(self.rpi2testpanel,text="Record",height=1,font=("Arial",8)) 
        self.R2.grid(row=1,column=1,padx=2,pady=2)
        self.S2 = tk.Button(self.rpi2testpanel,text="Status",height=1,font=("Arial",8)) 
        self.S2.grid(row=1,column=2,padx=2,pady=2)
        self.Check2 = tk.Button(self.rpi2testpanel,text="Check",height=1,font=("Arial",8)) 
        self.Check2.grid(row=1,column=3,padx=2,pady=2)
        TR2 = tk.Label(self.rpi2testpanel,text="Recorded %",font=("Arial",8))
        TR2.grid(row=2,column=2,padx=2,pady=2)
        TW2 = tk.Label(self.rpi2testpanel,text="Written %",font=("Arial",8))
        TW2.grid(row=2,column=3,padx=2,pady=2) 
 
##RPI 3
        self.rpi3testpanel = tk.Frame(self.right2_panel,width=194,height=80)
        self.rpi3testpanel.grid(row=2,column=1,pady=20,padx=3)
        self.rpi3testpanel.grid_propagate(False)
        #testo = tk.Label(self.rpi1testpanel,text="RPI1")
        #testo.grid(row=0,column=1)
        self.rpi3Stat = tk.StringVar
        self.rpi3Stat = "red"
        self.rpi3status = tk.Frame(self.rpi3testpanel,width=20,height=20,bg=self.rpi3Stat)
        self.rpi3status.grid(row=0,column=0,padx=2,pady=2)
        testo3 = tk.Label(self.rpi3testpanel,text="RPI3")
        testo3.grid(row=0,column=1)
        self.R3 = tk.Button(self.rpi3testpanel,text="Record",height=1,font=("Arial",8)) 
        self.R3.grid(row=1,column=1,padx=2,pady=2)
        self.S3 = tk.Button(self.rpi3testpanel,text="Status",height=1,font=("Arial",8)) 
        self.S3.grid(row=1,column=2,padx=2,pady=2)
        self.Check3 = tk.Button(self.rpi3testpanel,text="Check",height=1,font=("Arial",8)) 
        self.Check3.grid(row=1,column=3,padx=2,pady=2)
        TR3 = tk.Label(self.rpi3testpanel,text="Recorded %",font=("Arial",8))
        TR3.grid(row=2,column=2,padx=2,pady=2)
        TW3 = tk.Label(self.rpi3testpanel,text="Written %",font=("Arial",8))
        TW3.grid(row=2,column=3,padx=2,pady=2) 


        ##RPI 4
        self.rpi4testpanel = tk.Frame(self.right2_panel,width=194,height=80)
        self.rpi4testpanel.grid(row=3,column=1,pady=20,padx=3)
        self.rpi4testpanel.grid_propagate(False)
        #testo = tk.Label(self.rpi1testpanel,text="RPI1")
        #testo.grid(row=0,column=1)
        self.rpi4Stat = tk.StringVar
        self.rpi4Stat = "red"
        self.rpi4status = tk.Frame(self.rpi4testpanel,width=20,height=20,bg=self.rpi4Stat)
        self.rpi4status.grid(row=0,column=0,padx=2,pady=2)
        testo4 = tk.Label(self.rpi4testpanel,text="RPI4")
        testo4.grid(row=0,column=1)
        self.R4 = tk.Button(self.rpi4testpanel,text="Record",height=1,font=("Arial",8)) 
        self.R4.grid(row=1,column=1,padx=2,pady=2)
        self.S4 = tk.Button(self.rpi4testpanel,text="Status",height=1,font=("Arial",8)) 
        self.S4.grid(row=1,column=2,padx=2,pady=2)
        self.Check4 = tk.Button(self.rpi4testpanel,text="Check",height=1,font=("Arial",8)) 
        self.Check4.grid(row=1,column=3,padx=2,pady=2)
        TR4 = tk.Label(self.rpi4testpanel,text="Recorded %",font=("Arial",8))
        TR4.grid(row=2,column=2,padx=2,pady=2)
        TW4 = tk.Label(self.rpi4testpanel,text="Written %",font=("Arial",8))
        TW4.grid(row=2,column=3,padx=2,pady=2) 

        #COM
        self.COMtestpanel = tk.Frame(self.right2_panel,width=194,height=80)
        self.COMtestpanel.grid(row=4,column=1,pady=20,padx=3)
        self.COMtestpanel.grid_propagate(False)
        #testo = tk.Label(self.rpi1testpanel,text="RPI1")
        #testo.grid(row=0,column=1)
        self.COMStat = tk.StringVar
        self.COMStat = "red"
        self.COMstatus = tk.Frame(self.COMtestpanel,width=20,height=20,bg=self.COMStat)
        self.COMstatus.grid(row=0,column=0,padx=2,pady=2)
        testoCOM = tk.Label(self.COMtestpanel,text="Motor Controller")
        testoCOM.grid(row=0,column=1)
        self.CheckCOM = tk.Button(self.COMtestpanel,text="Check",height=1,font=("Arial",8)) 
        self.CheckCOM.grid(row=1,column=3,padx=2,pady=2)



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

        self.important_panel = tk.Frame(self.right_button_panel,width=150,height=130)
        self.important_panel.grid(column=2,row=0)
        self.important_panel.grid_propagate(False)

        self.autoheater = tk.Checkbutton(self.important_panel,text="Auto Heating")
        self.autoheater.grid(row=0,column=0,padx=2,pady=2)

        self.saveimgs = tk.Checkbutton(self.important_panel,text="Save images")
        self.saveimgs.grid(row=1,column=0,padx=2,pady=2)

        self.savetelem = tk.Checkbutton(self.important_panel,text="Save Telem")
        self.savetelem.grid(row=2,column=0,padx=2,pady=2)


        self.add_logo(self.left_button_panel)
        self.pingServer = tk.Label(self.left_button_panel,text="Connection status")
        self.pingServer.grid(row=0,column=1)

        self.connect_button = tk.Button(self.left_button_panel, text="Connect to server",height=1,font=("Arial",8), command=self.connect_socket, bg='white', fg='black')
        self.connect_button.grid(row=1,column=0)

        self.disconnect_button = tk.Button(self.left_button_panel, text="Disconnect to server" ,height=1,font=("Arial",8),command=self.disconnect_socket,bg='white', fg='black', state=tk.DISABLED)
        self.disconnect_button.grid(row=1,column=1)

        self.telemFrequency = tk.Scale(self.rates_panel,from_=1.2, to=10, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=0.1,variable=self.TelemFreqVal,label="Telemetry intervals (s)", command=self.change_TelemFreqVal)
        self.telemFrequency.pack(side=tk.TOP,padx=10)

        self.telemetryButton = tk.Button(self.left_button_panel, text="Telemetry currently off",height=1,font=("Arial",8), command=self.toggleTelem, bg='red', fg='white', state=tk.DISABLED)
        self.telemetryButton.grid(row=2,column=0)

        self.imgFrequency = tk.Scale(self.rates_panel,from_=10, to=60, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=self.ImgFreqVal,label="Image intervals (s)", command=self.change_ImgFreqVal)
        self.imgFrequency.pack(side=tk.TOP,padx=10)

        self.imgrate = tk.Scale(self.rates_panel,from_=32, to=1638, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=self.imgbaudrate,label="Image bit rate (Kbit/s)", command=self.change_imgbaudrate)
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
        self.AccEN = tk.Checkbutton(self.actions_panel,command=self.toggleActionButtons)
        self.AccEN.grid(column=3,row=1,padx=2,pady=4)

        self.C1Button = tk.Button(self.actions_panel,text="C1 EN",font=("Arial",7),  command=self.actuateC1 ,state=tk.DISABLED)
        self.C1Button.grid(column=0,row=2,padx=2,pady=4)
        self.C2Button = tk.Button(self.actions_panel,text="C2 EN",font=("Arial",7),  command=self.actuateC2 ,state=tk.DISABLED)
        self.C2Button.grid(column=1,row=2,padx=2,pady=4)
        self.C3Button = tk.Button(self.actions_panel,text="C3 EN",font=("Arial",7),  command=self.actuateC3 ,state=tk.DISABLED)
        self.C3Button.grid(column=2,row=2,padx=2,pady=4)
        self.C4Button = tk.Button(self.actions_panel,text="C4 EN",font=("Arial",7),  command=self.actuateC4 ,state=tk.DISABLED)
        self.C4Button.grid(column=3,row=2,padx=2,pady=4)
        self.PisEN = tk.Checkbutton(self.actions_panel,command=self.togglePisButtons)
        self.PisEN.grid(column=4,row=2,padx=2,pady=4)

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
    def HealthC1(self):
            #Send command
            #Receive information
        messagebox.showinfo("CHECK RESULTS","SD OK")
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
            #WatchPing(self.pingServer).start()
            #WatchTCP().start()
            WatchTelem(self.dataFormat,
                        self.tableLabels).start()
            WatchCamera(self.right_pic_panel,
                        self.panel,
                        self.timestamp).start()
        except Exception as e:
            print(f'An exception occurred in the live updates: {e}')

    ###### toggles ######

    def toggleActionButtons(self):
        if self.ActionButtons == 1:
            self.BW1Button.config(state=tk.DISABLED)
            self.BW2Button.config(state=tk.DISABLED)
            self.MOTButton.config(state=tk.DISABLED)
            self.ActionButtons = 0
        elif self.ActionButtons == 0:
            self.BW1Button.config(state=tk.NORMAL)
            self.BW2Button.config(state=tk.NORMAL)
            self.MOTButton.config(state=tk.NORMAL)
            self.ActionButtons = 1
        else:
            pass
    
    def togglePisButtons(self):
        if self.PisButtons == 1:
            self.C1Button.config(state=tk.DISABLED)
            self.C2Button.config(state=tk.DISABLED)
            self.C3Button.config(state=tk.DISABLED)
            self.C4Button.config(state=tk.DISABLED)
            self.PisButtons = 0
        elif self.PisButtons == 0:
            self.C1Button.config(state=tk.NORMAL)
            self.C2Button.config(state=tk.NORMAL)
            self.C3Button.config(state=tk.NORMAL)
            self.C4Button.config(state=tk.NORMAL)
            self.PisButtons = 1
        else:
            pass

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

    ###### sliders ######
    def change_TelemFreqVal(self, val):
        CommonData.TelemFreqVal = self.TelemFreqVal.get()
    
    def change_ImgFreqVal(self, val):
        CommonData.ImgFreqVal = self.ImgFreqVal.get()
    
    def change_imgbaudrate(self, val):
        CommonData.imgbaudrate = self.imgbaudrate.get()

############ Main ############

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
