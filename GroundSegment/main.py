import tkinter as tk

from tcp_client import TCPClientApp

HOST, PORT = '169.254.4.200', 5000  # Or use your Raspberry Pi's IP address

root = tk.Tk()
app = TCPClientApp(root, HOST, PORT)
root.mainloop()
