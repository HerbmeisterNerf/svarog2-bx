import socket
import time

if __name__ == "__main__":
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try: 
        while True:
            try:
                client_socket.connect(('192.168.78.2',8005))
                break
            except socket.error as e:
                print(f"Error: {e}")
                time.sleep(2)
        
        while True:
            s = client_socket.recv(1024)
            print(s.decode())

    finally:
        client_socket.close()

