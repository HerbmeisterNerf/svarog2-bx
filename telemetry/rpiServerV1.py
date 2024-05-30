import socket
from PIL import Image
import os
import io

server_TCP_port = 12000
welcome_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
welcome_socket.bind(('localhost',server_TCP_port))
welcome_socket.listen(1)

print('TCP Server running on port ', server_TCP_port)

#accept the TCP connection
connection_socket, TCPadd = welcome_socket.accept()
print("TCP connection from: ", TCPadd)


def compress_image_to_size(path, target_size):
    image = Image.open(path)
    quality = 100
    while True:
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=quality)
        img_size = img_buffer.tell()
       
        if img_size <= target_size:
            break
        quality -= 5
        if quality < 0:
            break
    compressed_path = path.replace('.jpg', '_compressed.jpg')
    image.save(compressed_path, format='JPEG', quality=quality)
    return compressed_path 

def send_image(path,target_size,connection_socket):
    #send the image via a TCP connection
    path_resize = compress_image_to_size(path, target_size)
    total_size = os.path.getsize(path_resize)
    connection_socket.sendall(f"{total_size}".encode('utf-8') + b'\n')  # Send the size of the image
    print("Size: ", total_size)
    with open(path_resize, 'rb') as f:
        while True:
            bytes_read = f.read(target_size)
            print("Bytes: ", bytes_read)
            if not bytes_read:
                break  # File transmitting is done
            connection_socket.sendall(bytes_read)
    print("Image sent.")

def send_video(path,target_size,connection_socket):
    total_size = os.path.getsize(path)
    connection_socket.sendall(f"{total_size}".encode('utf-8') + b'\n')  # Send the size of the video
    print("Size: ", total_size) 

    with open(path, 'rb') as f:
        while True:
            bytes_read = f.read(target_size)
            if not bytes_read:
                break  # File transmitting is done
            connection_socket.sendall(bytes_read)
    print("Video sent.")

while(1):   
    server_UDP_port = 13000
    server_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_UDP_socket.bind(('',server_UDP_port))
    print('UDP Server running on port ', server_UDP_port)
    cmsg, UCPadd = server_UDP_socket.recvfrom(2048)
    cmsg = cmsg.decode()
    print(cmsg)
    reply = "ACK"
    server_UDP_socket.sendto(reply.encode(),UCPadd)

    if cmsg == "image":
        #send the photo via a TCP connection
        send_image("image.jpg" , 1024, connection_socket)
    if cmsg == "video":
        #send the video via a TCP connection
        send_video("video.mp4" , 1024, connection_socket)
    if cmsg == "q":
        connection_socket.close()
        break


"""
while True:
    connection_socket, caddr = welcome_socket.accept()
    #notice recv and send instead of recvto and sendto
    #this is because the 'to' part is now implicit in the connection_socket
    cmsg = connection_socket.recv(1024)  	
    cmsg = cmsg.decode()
    if(cmsg.isalnum() == False):
        cmsg = "Not alphanumeric.";
    else:
        cmsg = "Alphanumeric";
    connection_socket.send(cmsg.encode())






#Now the loop that listens from clients
#As UDP is not connection oriented,the same UDP socket serves all clients

while True:
    #cadd below is the client process address
    cmsg, cadd = server_socket.recvfrom(2048)
    cmsg = cmsg.decode()
    if(cmsg.isalnum()==False):
        cmsg = "Not alphanumeric."
    else:
        cmsg = "Alphanumeric."

    #send reply message to the client process            
    server_socket.sendto(cmsg.encode(),cadd)
"""