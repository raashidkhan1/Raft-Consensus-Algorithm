import time
import random
import threading
import argparse
from xmlrpc.client import ServerProxy
from Server import Server
import atexit
import signal
class Node :

    def __init__(self, name, state, port, clusterNodes):
        self.node_name = name
        self.state = state
        self.port = port
        self.heartbeat_timeout = 10
        self.election_timeout = self.timer()
        self.term = 0
        self.run_thread = True
        self.cluster_nodes = clusterNodes
        self.heartbeat_received = False
        self.vote_count = 0
        # all valid states
        self.states = ["leader", "follower", "candidate"]
        print("Node initialized")

        print("Starting XMLRPC Server on node", self.node_name)
        self.server = Server(self.node_name, self.port)
        self.server.register_function(self.message_received, "message_received")
        self.server.start()
        print("XMLRPCServer started")

    ## basic functions
    def start_loop_thread(self):
        # infinite loops require a separate thread from main
        self.loop_thread = threading.Thread(target=self.node_self_loop, args=(self.state,))
        self.loop_thread.daemon = True # make it background
        self.loop_thread.start() ## self loop started in thread
        print("loop thread started")

    def is_valid_state(self):
        if self.state in self.states:
            return True
        return False

    # leader sends heartbeat to every node
    def send_heartbeat(self):
        all_heartbeat_threads = []
        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.append_entries, args=(node, self.port,))
            thread.start()
            all_heartbeat_threads.append(thread)
        
        for t in all_heartbeat_threads:
            t.join()

    # in case no hearbeat and timer ran out, self vote and request vote RPC
    def request_vote(self):
        pass

    # timer logic for 
    def timer(self):
        return random.randrange(100, 120)
    
    # append entries RPC -- might be optional??
    def append_entries(self, node, port):
        ## just make calls to node's message_received
        serverProxy = ServerProxy('http://'+node+':'+port)
        response = serverProxy.message_received()
        print(response.value+" on  "+node)
        

    def message_received(self):
        self.heartbeat_received = True
        return "recieved heartbeat"

    # election vote count check
    def check_election_winner(self):
        ## count votes, send win/lose response
        return False

    ### functions for each type of node

    def leader(self):
        print('Im a leader, bro!')
        while self.state == self.states[0]:
            time.sleep(self.heartbeat_timeout)
            self.send_heartbeat()

    def candidate(self):
        print('Im a candidate, bro!')
        while self.state == self.states[2]:
            self.term +=1
            self.vote_count +=1
            ## TODO: call election aka request votes rpc
            print(f'{self.node_name} wants to contest the leader election')
            if self.vote_count == 1:
                self.state = self.states[1]

    def follower(self):
        print('Im a follower, bro!')
        while self.state == self.states[1]:
            self.heartbeat_received = False
            time.sleep(self.election_timeout)
            if not self.heartbeat_received:
                self.state = self.states[2] 
                

    def node_self_loop(self, state):
        print('inside loop thread')
        index = self.states.index(state)

        while self.run_thread:
            if index == 0:
                self.leader()
            elif index == 1:
                self.follower()
            else:
                self.candidate()
    
    def terminate_self_loop_thread(self):
        self.run_thread = False
        self.loop_thread.join()

    def handle_exit(self):
        try:
            self.terminate_self_loop_thread()
            self.server.stop_server()
            self.server.join()
            print("Node stopped", args.name)
        except Exception as e:
            print("Couldn't handle exit! error: ", e)


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
    # not so good way of handling it, but don't see any working option yet, TODO: find option
    # except KeyboardInterrupt:
    #     my_node.handle_exit()
    except Exception as e:
        print("Exception", e)
    
            # exit handler *terminates threads and kills server
    atexit.register(my_node.handle_exit)
    signal.signal(signal.SIGTERM, my_node.handle_exit)
    signal.signal(signal.SIGINT, my_node.handle_exit)
    