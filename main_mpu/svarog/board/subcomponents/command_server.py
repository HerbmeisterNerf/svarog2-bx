import socket
import threading
from subcomponents.commands import handle_command


def _keepalive_sock(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        import struct
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except (AttributeError, OSError):
        pass


def _serve_client(client, addr, reader):
    _keepalive_sock(client)
    f = client.makefile("rw", buffering=1)
    try:
        for line in f:
            line = line.strip()
            if not line:
                continue
            resp = handle_command(line, reader)
            f.write(resp + "\n")
            f.flush()
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass
    except (OSError, ValueError):
        pass
    finally:
        try:
            f.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
    print(f"[cmd] client disconnected: {addr}")


def cmd_server(port, reader):
    print(f"[cmd] listening on 0.0.0.0:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind(("0.0.0.0", port))
            srv.listen()
            while True:
                try:
                    client, addr = srv.accept()
                except socket.timeout:
                    continue
                print(f"[cmd] client connected: {addr}")
                threading.Thread(target=_serve_client,
                                 args=(client, addr, reader), daemon=True).start()
    except OSError as e:
        print(f"[cmd] failed to bind port {port}: {e}")