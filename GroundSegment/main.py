import tkinter as tk

from TCPClientApp import TCPClientApp

HOST, PORT = "155.198.40.229", 12000  # Or use your Raspberry Pi's IP address

root = tk.Tk()
app = TCPClientApp(root, HOST, PORT)
root.mainloop()
