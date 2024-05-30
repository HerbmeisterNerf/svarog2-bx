import socket

# We just need to change "localhost" to the IP address of the rpi server
server_name = 'localhost'
server_TCP_port = 12000

#create a TCP client socket
client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Set up a TCP connection with the server
client_TCP_socket.connect((server_name, server_TCP_port))
print("TCP client running...")
print("Connecting to server at IP: ", server_name, " PORT: ", server_TCP_port)



#now we create a UDP client socket
def send_UDP_message(message, port=13000):
    server_UDP_port = port
    client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("UDP client running...")
    print("Connecting to server at IP: ", server_name, " PORT: ", server_UDP_port)

    client_UDP_socket.sendto(message.encode(),(server_name, server_UDP_port))
    msg, sadd = client_UDP_socket.recvfrom(2048)
    print(msg.decode())
    client_UDP_socket.close()

def save_image(connection_socket):
    print("Receiving image...")
    total_size = int(connection_socket.recv(1024).split(b'\n')[0])  # Receive the size of the image
    print("Size: ", total_size)
    received = 0

    with open("received_image.jpg", 'wb') as f:
        print("here")
        while received < total_size:
            print("iterating")
            bytes_read = connection_socket.recv(1024)

            if not bytes_read:
                break  # The socket is closed
            f.write(bytes_read)
            received += len(bytes_read)

    print("Image has been received." , bytes_read)

def save_video(connection_socket):
    print("Receiving video...")
    total_size = int(connection_socket.recv(1024).split(b'\n')[0])  # Receive the size of the video
    print("Size: ", total_size)
    received = 0

    with open("received_video.mp4", 'wb') as f:
        while received < total_size:
            bytes_read = connection_socket.recv(1024)
            print(f"Loading Video: {received/total_size*100}% ")
            if not bytes_read:
                break  # The socket is closed
            f.write(bytes_read)
            received += len(bytes_read)

    print("Video has been received.")

message= ""
while(message != "q"):
    message = input("Enter your command:")
    send_UDP_message(message)
    if message == "q":
        
        break
    elif message == "video":
        save_video(client_TCP_socket)
    elif message == "image":
        save_image(client_TCP_socket)

    print("got here")

"""

#take input from the user
msg = input("Enter a string to test if it is alphanumeric: ");

#send the message  to the udp server
client_socket.send(msg.encode())

#return values from the server
msg = client_socket.recv(1024)
print(msg.decode())
client_socket.close()







#take input from the user
msg = input("Enter a string to test if it is alphanumeric: ");

#send the message to the udp server
client_socket.sendto(msg.encode(),(server_name, server_port))

#return values from the server
msg, sadd = client_socket.recvfrom(2048)

#show output and close client
print(msg.decode())
client_socket.close()

"""