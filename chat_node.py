import socket
import threading
import json
import hashlib
import uuid
import sys
from typing import Dict, Tuple
import queue
from cryptography.fernet import Fernet
import time
import datetime

SIGNALING_SERVER_HOST = '127.0.0.1'
SIGNALING_SERVER_PORT = 5555

class ChatNode:
    def __init__(self, host: str, port: int, username: str):
        """
        Initialize a ChatNode instance.

        Args:
            host (str): The host address of the node.
            port (int): The port number of the node.
            username (str): The username of the node.
        """
        self.host = host
        self.port = port
        self.username = username
        self.id = self._generate_node_id()
        self.peers: Dict[str, Tuple[str, int, str]] = {}
        self.dht: Dict[str, Dict] = {}
        self.chat_name_to_id: Dict[str, str] = {}
        self.message_queue = queue.Queue()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.running = False
        self.seen_messages = set()
        self.replication_interval = 100
        self.ping_interval = 5
        self.ping_timeout = 15
        self.peer_status = {}
        self.last_ping_time = {}
        self.lock = threading.Lock()
        self.status_lock = threading.RLock()
        self.peer_addr_to_id = {}
        self.logical_clock = 0
        self.message_buffer = []
        self.next_message_index = 0
        self.latency_measurements = []
        self.message_count = 0
        self.start_time = None
        self.message_sizes = []



    def _generate_node_id(self) -> str:
        """
        Generate a unique node ID based on the host and port.

        Returns:
            str: The generated node ID.
        """
        return hashlib.sha1(f"{self.host}:{self.port}".encode()).hexdigest()[:10]

    def start(self):
        """
        Start the chat node and initialize all necessary threads.
        """
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._handle_user_input, daemon=True).start()
        threading.Thread(target=self._process_message_queue, daemon=True).start()
        threading.Thread(target=self._replicate_data, daemon=True).start()
        threading.Thread(target=self._ping_peers, daemon=True).start()
        threading.Thread(target=self._check_peer_status, daemon=True).start()
        threading.Thread(target=self._process_buffered_messages, daemon=True).start()
        
        self.start_time = time.time()

        print(f"\n=== P2P Chat Node Started ===")
        print(f"Username: {self.username}")
        print(f"Node ID: {self.id}")
        print(f"Listening on {self.host}:{self.port}")
        print("\nCommands:")
        print("/help - Show this help message")
        print("/peers - List connected peers")
        print("/create_chat <Chat Name> - Create a new chat and get a unique Chat ID")
        print("/join_chat <Chat ID> - Join an existing chat")
        print("/send_chat <Chat Name> <message> - Send a message to a specific chat")
        print("/quit - Exit the chat")
        print("=====================================\n")

    def _listen(self):
        """
        Listen for incoming messages and add them to the message queue.
        """
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode())
                self.message_queue.put((message, addr))
            except Exception as e:
                if self.running:
                    print(f"\nError handling incoming message: {e}")

    def _get_peer_id_from_addr(self, addr: Tuple[str, int]) -> str:
        """
        Generate a peer ID based on the address.

        Args:
            addr (Tuple[str, int]): The address tuple (host, port).

        Returns:
            str: The generated peer ID.
        """
        normalized_addr = ('127.0.0.1' if addr[0] == 'localhost' else addr[0], addr[1])
        return hashlib.sha1(f"{normalized_addr[0]}:{normalized_addr[1]}".encode()).hexdigest()[:10]

    def _process_message_queue(self):
        """
        Process messages from the message queue.
        """
        while self.running:
            try:
                message, addr = self.message_queue.get()
                self._handle_message(message, addr)
            except Exception as e:
                print(f"\nError processing message queue: {e}")

    def _process_buffered_messages(self):
        """
        Process buffered messages in order based on logical clocks.
        """
        while self.running:
            time.sleep(0.1)
            with self.lock:
                self.message_buffer.sort(key=lambda x: (x['logical_clock'], x['timestamp']))
                while self.message_buffer and self.message_buffer[0]['logical_clock'] <= self.logical_clock:
                    message = self.message_buffer.pop(0)
                    self._display_message(message)
                    self.next_message_index += 1

    def _display_message(self, message: dict):
        """
        Decrypt and display a chat message.

        Args:
            message (dict): The message dictionary.
        """
        try:
            chat_id = message['chat_id']
            sender_username = message['username']
            encrypted_content = message['content']
            timestamp = message['timestamp']
            logical_clock = message['logical_clock']
            cipher_suite = Fernet(self.dht[chat_id]['key'].encode())
            content = cipher_suite.decrypt(encrypted_content.encode()).decode()
            chat_name = self.dht[chat_id]['name']
            print(f"\n[{chat_name}] [{timestamp}] (LC:{logical_clock}) {sender_username}: {content}")
        except Exception as e:
            print(f"\nError displaying message: {e}")

    def _handle_message(self, message: dict, addr: Tuple[str, int]):
        """
        Handle different types of incoming messages.

        Args:
            message (dict): The message dictionary.
            addr (Tuple[str, int]): The address tuple (host, port).
        """
        msg_type = message.get('type')
        if msg_type == 'join_request':
            self._handle_join_request(message, addr)
        elif msg_type == 'chat':
            self._handle_chat_message(message)
        elif msg_type == 'chat_info_response':
            self._handle_chat_info_response(message)
        elif msg_type == 'replication':
            self._handle_replication_message(message)
        elif msg_type == 'ping':
            self._handle_ping_message(addr)
        elif msg_type == 'pong':
            self._handle_pong_message(addr)
        elif msg_type == 'peer_disconnected':
            self._handle_peer_disconnected_message(message)

    def _handle_peer_disconnected_message(self, message: dict):
        """
        Handle a peer disconnection message.

        Args:
            message (dict): The message dictionary.
        """
        peer_id = message['peer_id']
        peer_username = message['peer_username']
        with self.lock:
            if peer_id in self.peers:
                del self.peers[peer_id]
                del self.peer_status[peer_id]
                del self.last_ping_time[peer_id]
        print(f"\n>>> {peer_username} has disconnected <<<")

    def _handle_join_request(self, message: dict, addr: Tuple[str, int]):
        """
        Handle a join request from a peer.

        Args:
            message (dict): The message dictionary.
            addr (Tuple[str, int]): The address tuple (host, port).
        """
        chat_id = message['chat_id']
        peer_id = message['node_id']
        peer_username = message['username']
        peer_host, peer_port = addr
        if chat_id in self.dht:
            chat_info = self.dht[chat_id]
            if peer_username not in chat_info['participants']:
                chat_info['participants'].append(peer_username)
            normalized_addr = ('127.0.0.1' if peer_host == 'localhost' else peer_host, peer_port)
            with self.status_lock:
                current_time = time.time()
                self.peers[peer_id] = (normalized_addr[0], normalized_addr[1], peer_username)
                self.peer_status[peer_id] = True
                self.last_ping_time[peer_id] = current_time
                self.peer_addr_to_id[(normalized_addr[0], normalized_addr[1])] = peer_id
            self._send_message({
                'type': 'chat_info_response',
                'chat_id': chat_id,
                'chat_info': chat_info,
                'host': self.host,
                'port': self.port,
                'username': self.username,
                'node_id': self.id
            }, addr)
            print(f"\n>>> {peer_username} joined chat {chat_info['name']} <<<")

    def _handle_chat_message(self, message: dict):
        """
        Handle an incoming chat message.

        Args:
            message (dict): The message dictionary.
        """
        chat_id = message['chat_id']
        sender_username = message['username']
        message_id = message.get('message_id')
        sender_logical_clock = int(message.get('logical_clock', 0))
        send_time = message.get('send_time')

        if not message_id or message_id in self.seen_messages:
            return
        self.seen_messages.add(message_id)
        self.logical_clock = max(self.logical_clock, sender_logical_clock) + 1
        
        if chat_id in self.dht and sender_username != self.username:
            with self.lock:
                self.message_buffer.append(message)
                
        message['logical_clock'] = self.logical_clock
        for peer_id, peer_info in self.peers.items():
            peer_host, peer_port, peer_username = peer_info
            if peer_username != sender_username:
                self._send_message(message, (peer_host, peer_port))
                
        if send_time:
            receive_time = time.time()
            latency = receive_time - send_time
            self.latency_measurements.append(latency)
        
        self.message_count += 1
        
        message_size = sys.getsizeof(json.dumps(message))
        self.message_sizes.append(message_size)



    def _handle_chat_info_response(self, message: dict):
        """
        Handle a chat info response message.

        Args:
            message (dict): The message dictionary.
        """
        chat_id = message['chat_id']
        chat_info = message['chat_info']
        self.dht[chat_id] = chat_info
        self.chat_name_to_id[chat_info['name']] = chat_id
        normalized_addr = ('127.0.0.1' if message['host'] == 'localhost' else message['host'], message['port'])
        peer_id = message.get('node_id') or self._get_peer_id_from_addr((message['host'], message['port']))
        with self.status_lock:
            current_time = time.time()
            self.peers[peer_id] = (normalized_addr[0], normalized_addr[1], message['username'])
            self.peer_status[peer_id] = True
            self.last_ping_time[peer_id] = current_time
            self.peer_addr_to_id[(normalized_addr[0], normalized_addr[1])] = peer_id
        print(f"\nSuccessfully joined chat {chat_info['name']}. Participants: {chat_info['participants']}")

    def _handle_replication_message(self, message: dict):
        """
        Handle a replication message.

        Args:
            message (dict): The message dictionary.
        """
        chat_id = message['chat_id']
        chat_info = message['chat_info']
        self.dht[chat_id] = chat_info
        self.chat_name_to_id[chat_info['name']] = chat_id
        print(f"\nReplicated chat data for chat {chat_info['name']}")

    def _handle_ping_message(self, addr: Tuple[str, int]):
        """
        Handle a ping message from a peer.

        Args:
            addr (Tuple[str, int]): The address tuple (host, port).
        """
        normalized_addr = ('127.0.0.1' if addr[0] == 'localhost' else addr[0], addr[1])
        self._send_message({'type': 'pong'}, normalized_addr)

    def _handle_pong_message(self, addr: Tuple[str, int]):
        """
        Handle a pong message from a peer.

        Args:
            addr (Tuple[str, int]): The address tuple (host, port).
        """
        with self.status_lock:
            peer_id = self.peer_addr_to_id.get((addr[0], addr[1]))
            if peer_id and peer_id in self.peers:
                current_time = time.time()
                peer_host, peer_port, peer_username = self.peers[peer_id]
                self.last_ping_time[peer_id] = current_time
                self.peer_status[peer_id] = True

    def _send_message(self, message: dict, addr: Tuple[str, int]):
        """
        Send a message to a specified address.
    
        Args:
            message (dict): The message dictionary.
            addr (Tuple[str, int]): The address tuple (host, port).
        """
        try:
            normalized_addr = ('127.0.0.1' if addr[0] == 'localhost' else addr[0], addr[1])
            send_time = time.time()
            message['send_time'] = send_time  # Add send time to the message
            self.socket.sendto(json.dumps(message).encode(), normalized_addr)
        except Exception as e:
            print(f"\nError sending message to {addr}: {e}")


    def create_chat(self, chat_name: str):
        """
        Create a new chat with a specified name.

        Args:
            chat_name (str): The name of the chat.

        Returns:
            str: The unique chat ID.
        """
        chat_id = str(uuid.uuid4())
        key = Fernet.generate_key()
        self.dht[chat_id] = {
            'creator': self.username,
            'participants': [self.username],
            'key': key.decode(),
            'name': chat_name
        }
        self.chat_name_to_id[chat_name] = chat_id
        if self._register_chat(chat_id):
            print(f"\nChat '{chat_name}' created successfully! Share this Chat ID: {chat_id}")
        else:
            print("\nFailed to register chat with signaling server.")
        return chat_id

    def list_peers(self):
        """
        List all connected peers.
        """
        if not self.peers:
            print("\nNo connected peers.")
        else:
            print("\nConnected peers:")
            for peer_id, (peer_host, peer_port, peer_username) in self.peers.items():
                print(f"Peer ID: {peer_id}, Username: {peer_username}, Address: {peer_host}:{peer_port}")

    def join_chat(self, chat_id: str):
        """
        Join an existing chat using the chat ID.

        Args:
            chat_id (str): The unique chat ID.
        """
        creator_info = self._get_chat_creator(chat_id)
        if creator_info:
            peer_host, peer_port = creator_info
            peer_id = hashlib.sha1(f"{peer_host}:{peer_port}".encode()).hexdigest()[:10]
            with self.lock:
                self.peers[peer_id] = (peer_host, peer_port, self.username)
                self.peer_status[peer_id] = True
                self.last_ping_time[peer_id] = time.time()
            self._send_message({
                'type': 'join_request',
                'chat_id': chat_id,
                'node_id': self.id,
                'username': self.username
            }, (peer_host, peer_port))
        else:
            print(f"\nChat {chat_id} not found.")

    def send_chat(self, chat_name: str, content: str):
        """
        Send a chat message to a specified chat.

        Args:
            chat_name (str): The name of the chat.
            content (str): The content of the message.
        """
        chat_id = self.chat_name_to_id.get(chat_name)
        
        if not chat_id:
            print("\nInvalid Chat Name. Cannot send message.")
            return
            
        self.logical_clock += 1
        
        cipher_suite = Fernet(self.dht[chat_id]['key'].encode())
        encrypted_content = cipher_suite.encrypt(content.encode()).decode()
        current_time = datetime.datetime.now().isoformat()
        
        message = {
            'type': 'chat',
            'chat_id': chat_id,
            'username': self.username,
            'content': encrypted_content,
            'message_id': str(uuid.uuid4()),
            'timestamp': current_time,
            'logical_clock': self.logical_clock
        }
        self._display_message(message)
        for peer_id, peer_info in self.peers.items():
            self._send_message(message, (peer_info[0], peer_info[1]))

    def _handle_user_input(self):
        """
        Handle user input from the command line.
        """
        while self.running:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() == '/quit':
                    self.stop()
                    break
                elif user_input.lower() == '/help':
                    print("\nCommands:")
                    print("/help - Show this help message")
                    print("/peers - List connected peers")
                    print("/create_chat <Chat Name> - Create a new chat and get a unique Chat ID")
                    print("/join_chat <Chat ID> - Join an existing chat")
                    print("/send_chat <Chat Name> <message> - Send a message to a specific chat")
                    print("/quit - Exit the chat")
                elif user_input.lower() == '/peers':
                    self.list_peers()
                elif user_input.lower().startswith('/create_chat'):
                    _, chat_name = user_input.split(maxsplit=1)
                    self.create_chat(chat_name)
                elif user_input.lower().startswith('/join_chat'):
                    _, chat_id = user_input.split(maxsplit=1)
                    self.join_chat(chat_id)
                elif user_input.lower().startswith('/send_chat'):
                    _, chat_name, content = user_input.split(maxsplit=2)
                    self.send_chat(chat_name, content)
                else:
                    print("\nUnknown command. Type /help for help.")
            except Exception as e:
                print(f"\nError handling input: {e}")

    def stop(self):
        """
        Stop the chat node and close the socket.
        """
        print("\nShutting down...")
        self.running = False
        self._display_metrics()
        self.socket.close()
        sys.exit(0)

    def _register_chat(self, chat_id: str) -> bool:
        """
        Register the chat with the signaling server.

        Args:
            chat_id (str): The unique chat ID.

        Returns:
            bool: True if registration was successful, False otherwise.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SIGNALING_SERVER_HOST, SIGNALING_SERVER_PORT))
                s.send(f"REGISTER {chat_id} {self.host} {self.port}".encode())
                response = s.recv(1024).decode()
                return response == "REGISTERED"
        except Exception as e:
            print(f"Error registering chat: {e}")
            return False

    def _get_chat_creator(self, chat_id: str):
        """
        Get the creator of a chat from the signaling server.
    
        Args:
            chat_id (str): The unique chat ID.
    
        Returns:
            Tuple[str, int] or None: The address tuple (host, port) of the chat creator, or None if not found.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SIGNALING_SERVER_HOST, SIGNALING_SERVER_PORT))
                s.send(f"GET {chat_id} 0 0".encode())
                response = s.recv(1024).decode()
                if response == "NOT_FOUND":
                    return None
                else:
                    host, port = response.split()
                    return host, int(port)
        except Exception as e:
            print(f"Error getting chat creator: {e}")
            return None
    
    def _replicate_data(self):
        """
        Replicate chat data to all peers periodically.
        """
        while self.running:
            time.sleep(self.replication_interval)
            for chat_id, chat_info in self.dht.items():
                for peer_id in list(self.peers.keys()):
                    peer_info = self.peers.get(peer_id)
                    if peer_info:
                        peer_host, peer_port, peer_username = peer_info
                        self._send_message({
                            'type': 'replication',
                            'chat_id': chat_id,
                            'chat_info': chat_info
                        }, (peer_host, peer_port))
    
    def _ping_peers(self):
        """
        Ping all peers periodically to check their status.
        """
        while self.running:
            time.sleep(self.ping_interval)
            with self.status_lock:
                for peer_id, (peer_host, peer_port, peer_username) in list(self.peers.items()):
                    if peer_username != self.username:
                        try:
                            self._send_message({
                                'type': 'ping',
                                'node_id': self.id,
                                'username': self.username
                            }, (peer_host, peer_port))
                        except Exception as e:
                            print(f"Error sending ping to {peer_username} ({peer_host}:{peer_port}): {e}")
                            self.peer_status[peer_id] = False
    
    def _check_peer_status(self):
        """
        Check the status of peers and handle disconnections.
        """
        while self.running:
            time.sleep(self.ping_interval)
            disconnected_peers = []
            with self.status_lock:
                current_time = time.time()
                for peer_id, last_ping in self.last_ping_time.items():
                    if current_time - last_ping > self.ping_timeout:
                        peer_info = self.peers.get(peer_id)
                        if peer_info:
                            peer_host, peer_port, peer_username = peer_info
                            print(f"\nPeer {peer_username} ({peer_host}:{peer_port}) is offline.")
                            disconnected_peers.append((peer_id, peer_username))
                for peer_id, peer_username in disconnected_peers:
                    peer_info = self.peers[peer_id]
                    addr_key = (peer_info[0], peer_info[1])
                    self.peers.pop(peer_id, None)
                    self.peer_status.pop(peer_id, None)
                    self.last_ping_time.pop(peer_id, None)
                    self.peer_addr_to_id.pop(addr_key, None)
                    self._notify_peer_disconnection(peer_id, peer_username)
    
    def _notify_peer_disconnection(self, peer_id: str, peer_username: str):
        """
        Notify all other peers about the disconnection.
    
        Args:
            peer_id (str): The ID of the disconnected peer.
            peer_username (str): The username of the disconnected peer.
        """
        for other_peer_id, other_peer_info in self.peers.items():
            other_peer_host, other_peer_port, other_peer_username = other_peer_info
            self._send_message({
                'type': 'peer_disconnected',
                'peer_id': peer_id,
                'peer_username': peer_username
            }, (other_peer_host, other_peer_port))
            
    
    def _display_metrics(self):
        """
        Display the collected performance metrics.
        """
        if self.latency_measurements:
            avg_latency = sum(self.latency_measurements) / len(self.latency_measurements)
            print(f"\nAverage Latency: {avg_latency * 1000:.2f} ms")
    
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            throughput = self.message_count / elapsed_time
            print(f"Throughput: {throughput:.2f} messages/second")
        
        if self.message_sizes:
            avg_message_size = sum(self.message_sizes) / len(self.message_sizes)
            print(f"Average Message Size: {avg_message_size:.2f} bytes")
