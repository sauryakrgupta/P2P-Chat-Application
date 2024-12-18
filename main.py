import argparse
from chat_node import ChatNode

def main():
    parser = argparse.ArgumentParser(description='P2P Chat Node')
    parser.add_argument('--host', default='localhost', help='Host to listen on')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--username', required=True, help='Your username')

    args = parser.parse_args()
    node = ChatNode(args.host, args.port, args.username)
    node.start()

    try:
        while node.running:
            pass
    except KeyboardInterrupt:
        node.stop()

if __name__ == "__main__":
    main()
