############ standard libraries ############
import socket
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import queue
import os
from tkterminal import Terminal

############ custom libraries ############
from MessagePack import MessagePack
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from LiveUpdatesCamera import LiveUpdatesCamera
from CommonData import CommonData
from PortCommunication import PortCommunication

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
        self.TelemFreqVal = tk.DoubleVar()
        self.ImgFreqVal = tk.DoubleVar()
        self.imgbaudrate = tk.DoubleVar()

        ###### GUI Elements ######

        # Add logo
        #
        #Main two frames
        self.left_panel = tk.Frame(master,width=300,height=500,bg="grey")
        self.left_panel.grid(row=0,column=0)
        self.left_panel.grid_propagate(False)
        self.right_panel = tk.Frame(master,width=600,height=500,bg="white")
        self.right_panel.grid(row=0,column=1)
        self.right_panel.grid_propagate(False)

        #Button containment frame

        self.left_button_panel = tk.Frame(self.left_panel,width=300,height=100)
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
        
        # Frame for connection status and toggle button
        # self.status_frame = tk.Frame(master, bg='black')
        # self.status_frame.pack(pady=10)

        # self.button_frame = tk.Frame(master,bg='white')
        # self.button_frame.pack(pady=50)

        # # close app button
        # exit_button = tk.Button(self.status_frame, text="Exit", command=master.destroy) 
        # exit_button.pack(pady=20)

        # # other buttons
        # self.plotButton = tk.Button(self.status_frame, text="Hide Voltage Monitor", command=self.togglePlot, bg='white', fg='black')
        # self.plotButton.pack(side=tk.LEFT, padx=10)
        self.add_logo(self.left_button_panel)
        self.connect_button = tk.Button(self.left_button_panel, text="Connect to server",height=1,font=("Arial",8), command=self.connect_socket, bg='white', fg='black')
        self.connect_button.grid(row=1,column=0)

        self.disconnect_button = tk.Button(self.left_button_panel, text="Disconnect to server" ,height=1,font=("Arial",8),command=self.disconnect_socket,bg='white', fg='black', state=tk.DISABLED)
        self.disconnect_button.grid(row=1,column=1)

        self.telemFrequency = tk.Scale(self.rates_panel,from_=1.2, to=10, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=0.1,variable=self.TelemFreqVal,label="Telemetry intervals (s)")
        self.telemFrequency.pack(side=tk.TOP,padx=10)

        self.telemetryButton = tk.Button(self.left_button_panel, text="Telemetry currently off",height=1,font=("Arial",8), command=self.toggleTelem, bg='red', fg='white', state=tk.DISABLED)
        self.telemetryButton.grid(row=2,column=0)

        self.imgFrequency = tk.Scale(self.rates_panel,from_=10, to=60, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=self.ImgFreqVal,label="Image intervals (s)")
        self.imgFrequency.pack(side=tk.TOP,padx=10)

        self.imgrate = tk.Scale(self.rates_panel,from_=32, to=1638, orient="horizontal",width=5,font=("Arial",7),length=150,resolution=1,variable=self.imgbaudrate,label="Image bit rate (Kbit/s)")
        self.imgrate.pack(side=tk.TOP,padx=10)

        self.imageButton = tk.Button(self.left_button_panel, text="Camera currently off", height=1,font=("Arial",8),command=self.toggleCamera, bg='red', fg='white', state=tk.DISABLED)
        self.imageButton.grid(row=2,column=1)

        # #Action buttons
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



        # self.H2Button = tk.Button(self.button_frame,text="Heater 2",  command=self.actuateH2 ,state=tk.DISABLED)
        # self.H2Button.pack(side=tk.LEFT, padx=10)
        # self.H3Button = tk.Button(self.button_frame,text="Heater 3",   command=self.actuateH3 ,state=tk.DISABLED)
        # self.H3Button.pack(side=tk.LEFT, padx=10)
        # self.H4Button = tk.Button(self.button_frame,text="Heater 4",   command=self.actuateH4 ,state=tk.DISABLED)
        # self.H4Button.pack(side=tk.LEFT, padx=10)
        # self.H5Button = tk.Button(self.button_frame,text="Heater 5",   command=self.actuateH5 ,state=tk.DISABLED)
        # self.H5Button.pack(side=tk.LEFT, padx=10)
        # self.H6Button = tk.Button(self.button_frame,text="Heater 6",   command=self.actuateH6 ,state=tk.DISABLED)
        # self.H6Button.pack(side=tk.LEFT, padx=10)
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
        
        
        # # tabs
        # tabs = tk.ttk.Notebook(master)
        # tabs.pack(expand=1, fill='both')
        # self.tab1 = tk.Frame(tabs, bg='khaki1')
        # self.tab2 = tk.Frame(tabs, bg='lightgray')
        # tabs.add(self.tab1, text='Tab 1')
        # tabs.add(self.tab2, text='Tab 2')

        # # frames inside tab1
        
        # self.frame1_left = tk.Frame(self.tab1, bg='lightgray')
        # self.frame1_right = tk.Frame(self.tab1)
        # #self.frame1_terminal = tk.Frame(self.tab1, bg='lightgray')
        self.timestamp = tk.StringVar()
        self.timestamp.set('timestamp')
        self.imgtimestamp = tk.Label(self.right_pic_panel, textvariable = self.timestamp)
        self.imgtimestamp.pack()
        # self.frame1_left.grid(row=0, column=0, padx=10, pady=10)
        # self.frame1_right.grid(row=0, column=1, padx=10, pady=10)
        # #self.frame1_terminal.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        # # create terminal
        # #terminal = Terminal(bg = 'black', fg = 'white', pady=5, padx=5)
        # #terminal.pack(expand=True, fill='both')

        # # create list of data
        self.get_data_format()
        self.create_data_table()

        # # create image from camera
        self.add_image_camera(self.right_pic_panel,"camera.png")

        # # create plots
        # plt.style.use('dark_background')
        # self.fig, self.ax = plt.subplots()
        # self.xs, self.ys = [], []
        # self.line, = self.ax.plot(self.xs, self.ys, color='green')
        # self.create_plot(master, self.tab2)

        ###### Receive data ######
        # Start the thread
        self.start_live_updates()

        # Setup date format on x-axis
        # self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        # self.fig.autofmt_xdate()

############ Methods ############

    def exitfunc(self):
        self.master.destroy()


    ###### making it look nice ######

    def add_logo(self, frame):
        original_image = Image.open('logo.png')
        resized_image = original_image.resize((150, 45), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(resized_image)

        # Frame for the logo with a visible background
        #self.logo_frame = tk.Frame(master, bg='white')
        #self.logo_frame.pack(fill=tk.X)

        self.logo_label = tk.Label(frame, image=self.logo)
        self.logo_label.grid(column=0,row=0)

    ###### live images ######

    def add_image_camera(self, frame, filename):
        img = ImageTk.PhotoImage(Image.open(filename).resize((600, 350), Image.Resampling.LANCZOS))
        self.panel = tk.Label(frame, image=img)
        self.panel.image = img
        self.panel.pack()

    ###### plots ######

    def create_plot(self, master, frame=None):
        # Add title to the plot
        self.ax.set_title("Voltage Monitor", color='white')

        # Add horizontal grid lines
        self.ax.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Set labels color
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')

        # Set tick parameters color
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')

        self.canvas = FigureCanvasTkAgg(self.fig, master = frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Plot visibility flag
        self.plot_visible = True

    # def update_plot(self, data):
    #     try:
    #         voltage = float(data.split()[-1][:-1])  # Extract voltage value
    #         current_time = datetime.datetime.now()  # Use datetime object
    #         self.ys.append(voltage)
    #         self.xs.append(current_time)

    #         # Maintain a rolling window of the last 20 data points
    #         if len(self.ys) > 20:
    #             self.ys.pop(0)
    #             self.xs.pop(0)

    #         self.line.set_data(self.xs, self.ys)
    #         self.ax.relim()
    #         self.ax.autoscale_view()

    #         self.canvas.draw()
    #     except ValueError as e:
    #         print(f'Error parsing data: {e}')

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
        data = []
        for i in range(CommonData.telemetryParameters):
                data.insert(i, 0.0)

        # add text
        for i in range(CommonData.telemetryParameters):
            tk.Label(self.left_data_panel,font=("Arial",7), text=self.dataFormat.iloc[i, 0], bg='lightgray').grid(row=(1+i%18), column=(2*(i//18)), padx=2, pady=2)
        # add data
        LiveUpdatesTelemetry.update_data_table(data, self.left_data_panel, self.dataFormat)
    
    ###### live updates ######

    def start_live_updates(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        self.queue = queue.Queue()
        self.queue.put_nowait(self.processTelemetry())
        self.queue.put_nowait(self.processCamera())

    def processTelemetry(self):
        try:
            if CommonData.runTelemetry:
                LiveUpdatesTelemetry(self.queue,
                                    self.current_packet,
                                    self.dataFormat,
                                    self.left_data_panel).start()
            self.queue.put_nowait(self.master.after(int(self.TelemFreqVal.get()*1000), self.processTelemetry))
        except queue.Empty:
            self.queue.put_nowait(self.master.after(int(self.TelemFreqVal.get()*1000), self.processTelemetry))
        
    def processCamera(self):
        try:
            if CommonData.runCamera:
                LiveUpdatesCamera(self.queue,
                                self.right_pic_panel,
                                self.panel,self.timestamp,round(float(4096/self.imgbaudrate.get()*8/1000),3)).start()
            self.queue.put_nowait(self.master.after(int(self.ImgFreqVal.get()*1000), self.processCamera))
        except queue.Empty:
            self.queue.put_nowait(self.master.after(int(self.ImgFreqVal.get()*1000), self.processCamera))

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
    def togglePlot(self):
        '''
        TBD
        '''

        if self.plot_visible:
            self.canvas_widget.pack_forget()
            self.toggle_button.config(text="Show Voltage Monitor")
        else:
            self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            self.toggle_button.config(text="Hide Voltage Monitor")
        self.plot_visible = not self.plot_visible

############ Main ############

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
