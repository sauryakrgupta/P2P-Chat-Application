import socket
import threading

# Dictionary to store chat_id and (host, port) of the chat creator
chat_rooms = {}

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            command, chat_id, host, port = message.split()
            if command == "REGISTER":
                chat_rooms[chat_id] = (host, int(port))
                client_socket.send("REGISTERED".encode())
            elif command == "GET":
                if chat_id in chat_rooms:
                    creator_host, creator_port = chat_rooms[chat_id]
                    client_socket.send(f"{creator_host} {creator_port}".encode())
                else:
                    client_socket.send("NOT_FOUND".encode())
        except:
            break

    client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("Signaling server started on port 5555")

    try:
        while True:
            client_socket, addr = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
    except KeyboardInterrupt:
        print("\nShutting down the signaling server...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()