
############ standard libraries ############
import socket
import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import queue

############ custom libraries ############
from MessagePack import MessagePack
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from CommonData import CommonData

############ class ############
class TCPClientApp:

############ Initializer ############

    def __init__(self, master, HOST = "155.198.40.229", PORT = 12000):

        # TCP info
        self.HOST = HOST
        self.PORT = PORT

        # other variables
        CommonData.telemetryParameters = 35
        self.current_packet = MessagePack()

        self.master = master
        master.title("TCP Client")
        master.configure(bg='black')

        ###### GUI Elements ######

        # Add logo
        self.add_logo(master)

        # Frame for connection status and toggle button
        self.status_frame = tk.Frame(master, bg='black')
        self.status_frame.pack(pady=10)

        # close app button
        exit_button = tk.Button(self.status_frame, text="Exit", command=master.destroy) 
        exit_button.pack(pady=20)

        self.toggle_button = tk.Button(self.status_frame, text="Hide Voltage Monitor", command=self.toggle_plot, bg='white', fg='black')
        self.toggle_button.pack(side=tk.LEFT, padx=10)
        
        self.connect_button = tk.Button(self.status_frame, text="Connect to server", command=self.connect_socket,bg='white', fg='black')
        self.connect_button.pack(side=tk.LEFT, padx=10)

        self.disconnect_button = tk.Button(self.status_frame, text="Disconnect to server", command=self.disconnect_socket,bg='white', fg='black')
        self.disconnect_button.pack(side=tk.LEFT, padx=10)

        self.imagebutton = tk.Button(self.status_frame, text="Get image", command=self.request_image,bg='white', fg='black')
        self.imagebutton.pack(side=tk.LEFT, padx=10)
        
        # tabs
        tabs = tk.ttk.Notebook(master)
        tabs.pack(expand=1, fill='both')
        self.frame1 = tk.Frame(tabs, bg='khaki1')
        self.frame2 = tk.Frame(tabs, bg='lightgray')
        tabs.add(self.frame1, text='Tab 1')
        tabs.add(self.frame2, text='Tab 2')

        # frames inside frame1
        self.frame1_left = tk.Frame(self.frame1, bg='lightgray')
        self.frame1_right = tk.Frame(self.frame1)

        self.frame1_left.grid(row=0, column=0, padx=10, pady=10)
        self.frame1_right.grid(row=0, column=1, padx=10, pady=10)

        # create list of data
        self.get_data_format()
        self.create_data_table()

        # create image from camera
        self.add_image_camera(self.frame1_right,"camera.png")

        # create plots
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots()
        self.xs, self.ys = [], []
        self.line, = self.ax.plot(self.xs, self.ys, color='green')
        self.create_plot(master, self.frame2)

        ###### Receive data ######
        # Start the thread
        self.running = True
        self.start_live_updates()

        # Setup date format on x-axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

############ Methods ############

    ###### making it look nice ######

    def add_logo(self, master):
        original_image = Image.open('logo.png')
        resized_image = original_image.resize((900, 275), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(resized_image)

        # Frame for the logo with a visible background
        self.logo_frame = tk.Frame(master, bg='white')
        self.logo_frame.pack(fill=tk.X)

        self.logo_label = tk.Label(self.logo_frame, image=self.logo, bg='white')
        self.logo_label.pack()

    ###### live images ######

    def add_image_camera(self, frame,filename):
        img = ImageTk.PhotoImage(Image.open(filename).resize((500, 175), Image.Resampling.LANCZOS))
        self.panel = tk.Label(frame, image=img)
        self.panel.image = img
        self.panel.pack()

    def update_image(self,filename):
        img = ImageTk.PhotoImage(Image.open(filename).resize((500, 175), Image.Resampling.LANCZOS))
        self.panel.configure(image=img)
        self.panel.image = img

    ###### live plots ######

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

    ###### sockets ######

    def connect_socket(self):
        # TCP
        server_name = self.HOST # For the raspberry pi
        server_TCP_port = self.PORT
        CommonData.client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Set up a TCP connection with the server
        CommonData.client_TCP_socket.connect((server_name, server_TCP_port))
        CommonData.TCPSTATUS = True
        self.connect_button.configure(bg="green",fg="white")
        self.disconnect_button.configure(bg="red",fg="white")
        print("TCP client running...")
        print("Connecting to server at IP: ", server_name, " PORT: ", server_TCP_port)

    def disconnect_socket(self):
        CommonData.client_TCP_socket.close()
        CommonData.TCPSTATUS = False
        self.connect_button.configure(bg="white",fg="black")
        self.disconnect_button.configure(bg="white",fg="black")
        print("Closing Socket...")

    ###### getting images ######

    def open_UDP_img(self):
        # UDP
        client_UDP_port = 15000
        UDP_info = ("", client_UDP_port)
        self.client_UDP_socket_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_UDP_socket_img.bind(UDP_info)

    def close_UDP_img(self):
        self.client_UDP_socket_img.close()

    def printGUI(self,texto):
        label = tk.Label(self.status_frame,text=texto)
        label.pack()

    def request_image(self):
        filename = "receivedimage.jpg"
        self.open_UDP_img() 
        message = "image"
        CommonData.client_TCP_socket.send(message.encode())
        print("Receiving image...")
    
        msg, add = self.client_UDP_socket_img.recvfrom(1024)
        total_size = int(msg.split(b'\n')[0])  # Receive the size of the image
        print("Size: ", total_size)
        received = 0

        with open(filename, 'wb') as f:
            while received < total_size:
                bytes_read = self.client_UDP_socket_img.recvfrom(1024)[0]

                if not bytes_read:
                    break  # The socket is closed
                f.write(bytes_read)
                received += len(bytes_read)

        print("Image has been received." , bytes_read)
        self.update_image(filename)
        self.close_UDP_img()

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
        for i in range(CommonData.telemetryParameters):
            for j in range(4):
                self.dataFormat[j+1][i] = float(self.dataFormat[j+1][i])

    def create_data_table(self):
        data = []
        for i in range(CommonData.telemetryParameters):
                data.insert(i, 0.0)

        # add text
        for i in range(CommonData.telemetryParameters):
            tk.Label(self.frame1_left, text=self.dataFormat[0][i], bg='lightgray').grid(row=(1+i%15), column=(2*(i//15)), padx=10, pady=2)
        # add data
        LiveUpdatesTelemetry.update_data_table(data, self.frame1_left, self.dataFormat)

    def start_live_updates(self):
        self.queue = queue.Queue()
        LiveUpdatesTelemetry(self.queue,
                            self.current_packet,
                            self.dataFormat,
                            self.frame1_left,
                            self.running).start()
        self.master.after(100, self.process_queue)

    def process_queue(self):
        try:
            msg = self.queue.get_nowait()
        except queue.Empty:
            print("Queue is empty")

############ Main ############

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
