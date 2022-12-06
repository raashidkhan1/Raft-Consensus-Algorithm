import time
import random
import threading
import argparse
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy

class Node :

    def __init__(self, name, state, port, clusterNodes) -> None:
        self.node_name = name
        self.state = state
        self.port = port
        self.heartbeatTimeout = 100
        self.electionTimeout = random.randrange(100, 120)
        self.term = 0
        self.run_thread = True
        self.cluster_nodes = clusterNodes
        self.heartbeat_received = False
        # all valid states
        self.states = ["leader", "follower", "candidate"]
        self.thread = None

        self.server = SimpleXMLRPCServer((name, port),)
        self.server.register_function(self.message_received)

        self.server.serve_forever()
        
    ## basic functions

    def start_loop_thread(self):
        # infinite loops require a separate thread from main
        self.thread = threading.Thread(target=self.node_self_loop, args=self.state)
        self.thread.daemon = True # make it background
        self.thread.start() ## self loop started in thread

    def is_valid_state(self):
        if self.state in self.states:
            return True
        return False

    # leader sends heartbeat to every node
    def send_heartbeat(self):
        all_heartbeat_threads = []
        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.append_entries, args=(node, self.port))
            thread.start()
            all_heartbeat_threads.append(thread)
        
        for t in all_heartbeat_threads:
            t.join()

    # in case no hearbeat and timer ran out, self vote and request vote RPC
    def request_vote(self):
        pass

    # timer logic for 
    def timer(self):
        pass
    
    # append entries RPC -- might be optional??
    def append_entries(self, node, port):
        ## just make calls to node's message_received
        s = ServerProxy('http://'+node+':'+port)
        response = s.self.message_received()
        print(response.value+" "+node)
        

    def message_received(self):
        self.heartbeat_received = True
        return "i'm happy"

    # election vote count check
    def check_election_winner(self):
        pass

    ### functions for each type of node

    def leader(self):
        print('Im a leader, bro!')
        while self.state == "leader":
            time.sleep(self.heartbeatTimeout)
            self.send_heartbeat()

    def candidate(self):
        print('Im a candidate, bro!')
        while self.state == "candidate":
            pass

    def follower(self):
        print('Im a follower, bro!')
        while self.state == "follower":
            self.heartbeat_received = False

    def node_self_loop(self, state):
        index = self.states.index(state)

        while self.run_thread:
            if index == 0:
                self.leader()
            elif index == 1:
                self.follower()
            else:
                self.candidate()
             


if __name__ == '__main__':
    print('Im a working')
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--name", default=0, type=str, help='name of node like node102')
    argparser.add_argument("--port", default=8000, type=int, help="communication port for sending and listening messages")
    argparser.add_argument("--clusterNodes", nargs='+', default=[], type=str, help="nodes in the reserved cluster like node102 node103 node104")
    args = argparser.parse_args()

    default_state = "follower"

    # removing the current node from its cluster list
    cluster = [node for node in args.clusterNodes if node != args.name]

    # **experimental** incrementing the port number based on index, separate ports for separate node 
    port = args.port + args.clusterNodes.index(args.name)

    my_node = Node(args.name, default_state, port, cluster)
    try:
        #initialze node
        print("Starting node", args.name)
        if my_node.is_valid_state():
            my_node.start_loop_thread()
        print("Started node", args.name)
    finally:
        # terminate thread(s)
        my_node.run_thread = False
        my_node.thread.join()
        print("Node stopped", args.name)
