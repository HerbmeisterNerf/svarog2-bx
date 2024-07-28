import socket
import tkinter as tk
import tkinter.ttk as ttk
# from tkinter import simpledialog
from PIL import Image, ImageTk
import threading
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import numpy as np
import time
import pandas as pd
from datetime import datetime

class TCPClientApp:

############ Initializer ############

    def __init__(self, master, HOST = "155.198.40.229", PORT = 12000):
        
        # TCP info
        self.HOST = HOST
        self.PORT = PORT
        self.TCPSTATUS = 0

        self.master = master
        master.title("TCP Client")
        master.configure(bg='black')

        ###### GUI Elements ######

        # Add logo
        self.add_logo(master)

        # Frame for connection status and toggle button
        self.status_frame = tk.Frame(master, bg='black')
        self.status_frame.pack(pady=10)

        # self.connect_label = tk.Label(self.status_frame, text="Connected to the server!", bg='white', fg='black')
        # self.connect_label.pack(side=tk.LEFT, padx=10)

        self.toggle_button = tk.Button(self.status_frame, text="Hide Voltage Monitor", command=self.toggle_plot, bg='white', fg='black')
        self.toggle_button.pack(side=tk.LEFT, padx=10)

        # self.response_label = tk.Label(master, text="", bg='black', fg='white')
        # self.response_label.pack(pady=10)
        
        self.connect_button = tk.Button(self.status_frame, text="Connect to server", command=self.connect_socket,bg='white', fg='black')
        self.connect_button.pack(side=tk.LEFT, padx=10)

        self.disconnect_button = tk.Button(self.status_frame, text="Disconnect to server", command=self.disconnect_socket,bg='white', fg='black')
        self.disconnect_button.pack(side=tk.LEFT, padx=10)
        
        # tabs
        tabs = tk.ttk.Notebook(master)
        tabs.pack(expand=1, fill='both')
        self.frame1 = tk.Frame(tabs, bg='khaki1')
        self.frame2 = tk.Frame(tabs, bg='lightgray')
        tabs.add(self.frame1, text='Tab 1')
        tabs.add(self.frame2, text='Tab 2')

        # frames inside frame1
        self.frame1_left = tk.Frame(self.frame1)
        self.frame1_right = tk.Frame(self.frame1)

        self.frame1_left.grid(row=0, column=0, padx=10, pady=10)
        self.frame1_right.grid(row=0, column=1, padx=10, pady=10)

        # create list of data
        self.get_data_format()
        self.create_data_table()

        # create image from camera
        self.add_image_camera(self.frame1_right)

        # create plots
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots()
        self.xs, self.ys = [], []
        self.line, = self.ax.plot(self.xs, self.ys, color='green')
        self.create_plot(master, self.frame2)

        ###### Receive data ######
        # Start the thread
        self.running = True
        self.thread = threading.Thread(target=self.receive_data)
        self.thread.start()

        # Setup date format on x-axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

############ Methods ############
    def add_logo(self, master):
        original_image = Image.open('logo.png')
        resized_image = original_image.resize((900, 275), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(resized_image)

        # Frame for the logo with a visible background
        self.logo_frame = tk.Frame(master, bg='white')
        self.logo_frame.pack(fill=tk.X)

        self.logo_label = tk.Label(self.logo_frame, image=self.logo, bg='white')
        self.logo_label.pack()

    def add_image_camera(self, frame):
        img = ImageTk.PhotoImage(Image.open('camera.png').resize((500, 175), Image.Resampling.LANCZOS))
        panel = tk.Label(frame, image=img)
        panel.image = img
        panel.pack()
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

    def toggle_plot(self):
        if self.plot_visible:
            self.canvas_widget.pack_forget()
            self.toggle_button.config(text="Show Voltage Monitor")
        else:
            self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            self.toggle_button.config(text="Hide Voltage Monitor")
        self.plot_visible = not self.plot_visible

    def receive_data(self):
        while self.running:
            time.sleep(1)
            
            try:
                # data = self.sock.recv(1024).decode()
                if self.TCPSTATUS == 1:
                    self.request_telemetry()

                now = datetime.now()
                data = []
                for i in range(35):
                    if 15 <= i <= 33:
                        data.insert(i, 'ON')
                    else:
                        data.insert(i, now.second)
                self.update_data_table(data)


                # if data:
                    # print(f"Received: {data}")  # Debugging statement
                    # if "Voltage:" in data:
                    #     self.update_plot(data)
                    # else:
                    #     self.update_response_label(f"Received: {data}")
                # else:
                #     print("Received empty data")
            except Exception as e:
                print(f'An exception occurred: {e}')
                break

    def connect_socket(self):

        # TCP
        server_name = self.HOST # For the raspberry pi
        server_TCP_port = self.PORT
        self.client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Set up a TCP connection with the server
        self.client_TCP_socket.connect((server_name, server_TCP_port))
        self.TCPSTATUS = 1
        self.connect_button.configure(bg="green",fg="white")
        self.disconnect_button.configure(bg="red",fg="white")
        print("TCP client running...")
        print("Connecting to server at IP: ", server_name, " PORT: ", server_TCP_port)

    def disconnect_socket(self):
        self.client_TCP_socket.close()
        self.TCPSTATUS = 0
        self.connect_button.configure(bg="white",fg="black")
        self.disconnect_button.configure(bg="white",fg="black")
        print("Closing Socket...")
    def open_UDP(self):
        # UDP
        client_UDP_port = 11000
        UDP_info = ("", client_UDP_port)
        self.client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_UDP_socket.bind(UDP_info)
    def close_UDP(self):
        self.client_TCP_socket.close()
    def request_telemetry(self):
        self.open_UDP() 
        message = "telemetry"
        self.client_TCP_socket.send(message.encode())
        bytes_read = self.client_UDP_socket.recvfrom(1024)
        print(bytes_read[0].decode("utf-8"))
    # def update_response_label(self, text):
    #     if self.response_label.winfo_exists():
    #         self.response_label.config(text=text)

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

    def get_data_format(self):
        self.dataFormat = pd.read_csv('dataFormat.csv', header=None)
        for i in range(35):
            for j in range(4):
                if 15 <= i <= 33:
                    pass
                else:
                    self.dataFormat[j+1][i] = float(self.dataFormat[j+1][i])

    def create_data_table(self):
        # mock up data   
        now = datetime.now()
        data = []
        for i in range(35):
            if 15 <= i <= 33:
                data.insert(i, 'ON')
            else:
                data.insert(i, now.second)

        # add text
        for i in range(len(self.dataFormat[0])):
            tk.Label(self.frame1_left, text=self.dataFormat[0][i]).grid(row=(1+i%15), column=(2*(i//15)), padx=10, pady=2)
        # add data
        self.update_data_table(data)

    def update_data_table(self, data):
        for i in range(len(data)):
            # clear contents
            tk.Label(self.frame1_left, text='000', bg='lightgray', fg='lightgray').grid(row=(1+i%15), column=(1+2*(i//15)), padx=30, pady=3)

            # set contents
            colourFG = 'black'
            if isinstance(data[i], str):
                if self.dataFormat[0][i] == 'OFF':
                    colourBG = 'orange'
                else:
                    colourBG = 'green'
                    colourFG = 'white'
            else:
                if data[i] < self.dataFormat[1][i] or data[i] > self.dataFormat[4][i]:
                    colourBG = 'red'
                elif self.dataFormat[1][i] < data[i] and data[i] < self.dataFormat[2][i]:
                    colourBG = 'orange'
                elif self.dataFormat[3][i] < data[i] and data[i] < self.dataFormat[4][i]:
                    colourBG = 'orange'
                else:
                    colourBG = 'green'
                    colourFG = 'white'
            tk.Label(self.frame1_left, text=data[i], bg=colourBG, fg=colourFG).grid(row=(1+i%15), column=(1+2*(i//15)), padx=30, pady=3)

############ Main ############

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
