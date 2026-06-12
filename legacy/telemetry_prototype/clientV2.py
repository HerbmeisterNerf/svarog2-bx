import socket
import threading
from messagePack import MessagePack

# We just need to change "localhost" to the IP address of the rpi server
#server_name = 'localhost' # When testing in own computer
server_name = "192.168.211.10" # For the raspberry pi
server_TCP_port = 12000

# Telemetry data


def receive_telemetry(connection_socket, stop_event):
    while not stop_event.is_set():
        try:
            telemetry_data = connection_socket.recv(1024)
            if telemetry_data:
                print("Telemetry data received: ", telemetry_data.decode())
            else:
                break  # Connection closed
        except socket.error as e:
            print(f"Socket error: {e}")
            break



#create a TCP client socket
client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Set up a TCP connection with the server
client_TCP_socket.connect((server_name, server_TCP_port))
print("TCP client running...")
print("Connecting to server at IP: ", server_name, " PORT: ", server_TCP_port)


def save_image(client_UDP_socket):
    print("Receiving image...")
    
    msg, add = client_UDP_socket.recvfrom(1024)
    total_size = int(msg.split(b'\n')[0])  # Receive the size of the image
    print("Size: ", total_size)
    received = 0

    with open("received_image.jpg", 'wb') as f:
        print("here")
        while received < total_size:
            print("iterating")
            bytes_read = client_UDP_socket.recvfrom(1024)[0]

            if not bytes_read:
                break  # The socket is closed
            f.write(bytes_read)
            received += len(bytes_read)

    print("Image has been received." , bytes_read)
    client_UDP_socket.close()

def save_video(client_UDP_socket):
    print("Receiving video...")
    msg, add = client_UDP_socket.recvfrom(1024)
    print("msg: ", msg)
    total_size = int(msg.split(b'\n')[0])  # Receive the size of the image
    print("Size: ", total_size)
    received = 0

    with open("received_video.mp4", 'wb') as f:
        while received < total_size:
            bytes_read = client_UDP_socket.recvfrom(1024)[0]
            print(f"Loading Video: {received/total_size*100}% ")
            if not bytes_read:
                break  # The socket is closed
            f.write(bytes_read)
            received += len(bytes_read)

    print("Video has been received.")
    client_UDP_socket.close()

def start_telemetry(client_TCP_socket):
    client_TCP_socket.send("telemetry".encode())
    telemetry_thread = threading.Thread(target=receive_telemetry, args=(client_TCP_socket, stop_event))
    telemetry_thread.start()
    print("Telemetry started.")
    return telemetry_thread

def stop_telemetry(client_TCP_socket):
    print
    client_TCP_socket.send("stop".encode())
    print("Stopping telemetry...")
    stop_event.set()
    print("Telemetry stopped.")
    

message= ""
client_UDP_port = 11000
UDP_info = ("", client_UDP_port)

stop_event = threading.Event()
telemetry_thread = None
#telemetry_thread.start()

while(message != "q"):
    message = input("Enter your command:")

    client_TCP_socket.send(message.encode()) #send the command to the server via TCP
    #ack = client_TCP_socket.recv(1024) #wait for the server to confirm the message was received
    #print(ack.decode())

    client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_UDP_socket.bind(UDP_info)
    print(f"Listening for UDP on port {UDP_info[1]}, from {UDP_info[0]}...")

    
    if message == "q":
        break
    if message == "video":
        save_video(client_UDP_socket)
    if message == "image":
        save_image(client_UDP_socket)
    if message == "telemetry":
        telemetry_thread = start_telemetry(client_TCP_socket)
    if message == "stop":
        stop_telemetry(client_TCP_socket)
        telemetry_thread.join()
    print("looping")
stop_event.set()
client_TCP_socket.close()


print("Connection closed.")
