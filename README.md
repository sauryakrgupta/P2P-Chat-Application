# P2P Chat Application
A decentralized peer-to-peer (P2P) chat application built with Python that enables secure, real-time messaging without relying on centralized servers. The system is designed for scalability, resilience, and privacy, ensuring robust communication across distributed networks.

### Features

+ **Decentralized Architecture**: Eliminates single points of failure with peer-to-peer communication using UDP sockets.

+ **Secure Messaging**: Ensures confidentiality with Fernet symmetric encryption for end-to-end secure chats.
 
+ **Causal Message Ordering**: Maintains the correct sequence of events using logical clocks.
 
+ **Dynamic Peer Management**: Supports seamless peer discovery and failure detection using a lightweight signaling server.
 
+ **Data Replication**: Preserves chat history across nodes for availability during node failures.
 
+ **Multithreading**: Handles concurrent operations like message queuing, peer status monitoring, and data replication efficiently.

***Prerequisites***

Python 3.6 or higher
cryptography library

**Install dependencies**: bashCopypip install cryptography

### Running the Application

Start the signaling server:

bashCopypython signaling_server.py

Run a chat node:

bashCopypython main.py --host localhost --port 5000 --username Alice

Create a chat room:

plaintextCopy/create_chat MyChatRoom

Join the chat room from another node:

bashCopypython main.py --host localhost --port 5001 --username Bob
plaintextCopy/join_chat <Chat ID>

Send a message:

plaintextCopy/send_chat MyChatRoom Hello, everyone!
Technologies Used

Python 3.6+
UDP Sockets
Fernet Encryption (from cryptography library)
Logical Clocks for event ordering
Multithreading for concurrent tasks

## Contributing
Feel free to fork, clone, and contribute to this project. Suggestions for improvements or additional features are always welcome.
