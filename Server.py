from threading import Thread
from xmlrpc.server import SimpleXMLRPCServer

class Server(Thread):
    def __init__(self, node_name, port) -> None:
        super().__init__()
        self.server = SimpleXMLRPCServer((node_name, port))

    def run(self) -> None:
        self.server.serve_forever()

    def register_function(self, function, function_alias):
        self.server.register_function(function, function_alias)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
