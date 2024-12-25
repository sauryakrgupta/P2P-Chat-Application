# P2P Chat Application
A decentralized peer-to-peer (P2P) chat application built with Python that enables secure, real-time messaging without relying on centralized servers. The system is designed for scalability, resilience, and privacy, ensuring robust communication across distributed networks.


## Features

+ **Decentralized Architecture**: Eliminates single points of failure with peer-to-peer communication using UDP sockets.

+ **Secure Messaging**: Ensures confidentiality with Fernet symmetric encryption for end-to-end secure chats.
 
+ **Causal Message Ordering**: Maintains the correct sequence of events using logical clocks.
 
+ **Dynamic Peer Management**: Supports seamless peer discovery and failure detection using a lightweight signaling server.
 
+ **Data Replication**: Preserves chat history across nodes for availability during node failures.
 
+ **Multithreading**: Handles concurrent operations like message queuing, peer status monitoring, and data replication efficiently.

***Prerequisites***

Python 3.6 or higher
cryptography library

**Install dependencies**:```pip install cryptography```

## Running the Application 

**Start the signaling server**:```python signaling_server.py```

**Run a chat node**:
python main.py --host localhost --port 5000 --username Alice

## General Commands
1. Show Help:
   
Display a list of all available commands: ```/help```

2. Exit Application:
   
Quit the current chat node session: ```/quit```

## Chat Room Management
3. Create a Chat Room:
   
Create a new chat room and get a unique Chat ID: ```/create_chat <Chat Name>```

4. Join an Existing Chat Room:
   
Join a chat room using the Chat ID provided:```/join_chat <Chat ID> ```

## Messaging

5. Send a Message:
   
Send a message to a specific chat room:```/send_chat <Chat Name> <Message>```

## Peer Management
6. List Connected Peers:
   
View all connected peers:```/peers```

**These commands enable seamless interaction with the P2P chat application, covering room management, messaging, and peer connectivity.**
 

:globe_with_meridians: ## Technologies Used
1. Python 3.6+
2. UDP Sockets
3. Fernet Encryption (from cryptography library)
4. Logical Clocks for event ordering
5. Multithreading for concurrent tasks

## Contributing
Feel free to fork, clone, and contribute to this project. Suggestions for improvements or additional features are always welcome.
