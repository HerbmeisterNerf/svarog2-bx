import socket
import tkinter as tk
# from tkinter import simpledialog
from PIL import Image, ImageTk
import threading
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

class TCPClientApp:
    def __init__(self, master, HOST = '169.254.4.200', PORT = 5000):
        self.master = master
        master.title("TCP Client")
        master.configure(bg='black')

        self.server_address = (HOST, PORT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.sock.connect(self.server_address)

        # GUI Elements
        original_image = Image.open('logo.png')
        resized_image = original_image.resize((900, 275), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(resized_image)

        # Frame for the logo with a visible background
        self.logo_frame = tk.Frame(master, bg='white')
        self.logo_frame.pack(fill=tk.X)

        self.logo_label = tk.Label(self.logo_frame, image=self.logo, bg='white')
        self.logo_label.pack()

        # Frame for connection status and toggle button
        self.status_frame = tk.Frame(master, bg='black')
        self.status_frame.pack(pady=10)

        self.connect_label = tk.Label(self.status_frame, text="Connected to the server!", bg='white', fg='black')
        self.connect_label.pack(side=tk.LEFT, padx=10)

        self.toggle_button = tk.Button(self.status_frame, text="Hide Voltage Monitor", command=self.toggle_plot, bg='white', fg='black')
        self.toggle_button.pack(side=tk.LEFT, padx=10)

        self.response_label = tk.Label(master, text="", bg='black', fg='white')
        self.response_label.pack(pady=10)

        # Matplotlib elements with dark theme
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots()
        self.xs, self.ys = [], []
        self.line, = self.ax.plot(self.xs, self.ys, color='green')

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

        self.canvas = FigureCanvasTkAgg(self.fig, master)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Plot visibility flag
        self.plot_visible = True

        # Start the thread for receiving data
        self.running = True
        # self.thread = threading.Thread(target=self.receive_data)
        # self.thread.start()

        # Setup date format on x-axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

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
            try:
                data = self.sock.recv(1024).decode()
                if data:
                    print(f"Received: {data}")  # Debugging statement
                    if "Voltage:" in data:
                        self.update_plot(data)
                    else:
                        self.update_response_label(f"Received: {data}")
                else:
                    print("Received empty data")
            except Exception as e:
                print(f'An exception occurred: {e}')
                break

    def update_response_label(self, text):
        if self.response_label.winfo_exists():
            self.response_label.config(text=text)

    def update_plot(self, data):
        try:
            voltage = float(data.split()[-1][:-1])  # Extract voltage value
            current_time = datetime.datetime.now()  # Use datetime object
            self.ys.append(voltage)
            self.xs.append(current_time)

            # Maintain a rolling window of the last 20 data points
            if len(self.ys) > 20:
                self.ys.pop(0)
                self.xs.pop(0)

            self.line.set_data(self.xs, self.ys)
            self.ax.relim()
            self.ax.autoscale_view()

            self.canvas.draw()
        except ValueError as e:
            print(f'Error parsing data: {e}')

if __name__ == '__main__':
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
