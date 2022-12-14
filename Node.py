import socket
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
        self.heartbeat_timeout = 1
        self.election_timeout = self.timer()
        self.term = 0
        self.run_thread = True
        self.cluster_nodes = clusterNodes
        self.heartbeat_received = False
        self.vote_count = float(0)

        # all valid states
        self.states = ["leader", "follower", "candidate"]

       #Experiment to check if port is active for rpc server not working
 #       sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 #       result = sock.connect_ex((self.node_name,self.port))


        print(f"{self.node_name} says :Node initialized", flush=True)
        print(f"{self.node_name} says :Starting XMLRPC Server on node", self.node_name)
        self.server = Server(self.node_name, self.port)
        self.server.register_function(self.message_received, "message_received")
        self.server.register_function(self.send_vote, "send_vote")
        self.server.start()
        print(f"{self.node_name} says :XMLRPCServer started", flush=True)
#        sock.close()

        ##testing with node107 as leader
        # if self.node_name == "node107":
        #     self.state="leader"

        ## controlling explicitly from main to catch exceptions
        # self.start_loop_thread()


    ## basic functions
    def start_loop_thread(self):
        # infinite loops require a separate thread from main
        try:
            self.loop_thread = threading.Thread(target=self.node_self_loop())
            self.loop_thread.daemon = True # make it background
            self.loop_thread.start() ## self loop started in thread
            print(f"{self.node_name} says :loop thread started", flush=True)
            while self.loop_thread.is_alive():
                self.loop_thread.join(1)
        except KeyboardInterrupt:
            self.handle_exit()

    def is_valid_state(self):
        if self.state in self.states:
            return True
        return False

    # leader sends heartbeat to every node
    def send_heartbeat(self):
        all_heartbeat_threads = []
        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.append_entries, args=(node['name'], node['port']))
            thread.start()
            all_heartbeat_threads.append(thread)

        for t in all_heartbeat_threads:
            t.join()

    # in case no hearbeat and timer ran out, self vote and request vote RPC
    def request_vote(self, node, port):
        with ServerProxy ('http://'+node+':'+ str(port)) as rpc_call:

            print(f"{self.node_name} says :requesting vote from:", node)

            response = rpc_call.send_vote(self.term)

            if response:
                print(f"Node, {node} sent vote", flush=True)
                self.vote_count += 1.0
            else :
                print(f"{self.node_name} says :Did not receive vote", flush=True)
                return

    def send_vote(self, term):
        if self.state != self.states[2] and self.term < term:
            return True
        else:
            print(f"{self.node_name} says :Iam a candidate or your current term is low, no voting", flush=True)
            return False

    # timer logic for
    def timer(self):
        return random.randrange(1, 5)

    def append_entries(self, node, port):
        with ServerProxy ('http://'+node+':'+ str(port)) as rpc_call:

            print(f"{self.node_name} says :Sending heartbeat to:",node)

            response = rpc_call.message_received(self.term, self.node_name)

            if response:
                print(f"Node, {node} received hearbeats", flush=True)
                if(self.term < response):
                    print(f"{self.node_name} says degrading to follower", flush=True)
                    self.term = response
                    self.state = self.states[1]
                    
            else :
                print(f"{self.node_name} says :Did not receive", flush=True)
                return

    def message_received(self, term, leader_node):
        self.heartbeat_received = True
        print(f"{self.node_name} says :I'm node:", self.node_name)
        # reset timer
        self.election_timeout = self.timer()
        if self.term < term: 
            self.term = term            
            return term
        elif self.term > term:
            print(f"{self.node_name} rejecting your hearbeat: ", leader_node)
            return self.term
        else:
            return term


    ### functions for each type of node

    def leader(self):
        print(f"{self.node_name} says I'm a leader man", flush=True)
        self.send_heartbeat()

    def candidate(self):
        print(f"{self.node_name} says I'm a candidate man", flush=True)
        self.vote_count +=1
        self.term +=1
        all_request_threads = []

        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.request_vote, args=(node['name'], node['port']))
            thread.start()
            all_request_threads.append(thread)

        for t in all_request_threads:
            t.join()
        
        min_vote = 0.5 * (float(len(self.cluster_nodes))+1.0)

        ## check vote count
        if self.vote_count >= min_vote:
            print(f"{self.node_name} says: Iam the leader now bitch", flush=True)
            self.state = self.states[0]
            self.vote_count = 0
        else:
            print(f"{self.node_name} says: failed to collect votes, becoming follower again", flush=True)
            self.state = self.states[1]
            self.vote_count = 0

    def follower(self):
        print(f"{self.node_name} says I'm a follower man", flush=True)
        self.heartbeat_received = False
        time.sleep(self.election_timeout)
        ## TODO: check leader term and sync own term

        print(f"{self.node_name} says :Follower says heartbeat :", self.heartbeat_received)
        if not self.heartbeat_received:
           self.state=self.states[2]


    def node_self_loop(self):
       #for testing only
        print(f"{self.node_name} says starting my self loop")
        # while(self.run_thread):
        for i in range(5):
            if self.state == self.states[0]:
                time.sleep(1)
                self.leader()
            elif self.state == self.states[1]:
                time.sleep(1)
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
            print(f"{self.node_name} says :Node stopped", args.name)
        except Exception as e:
            print(f"{self.node_name} says :Couldn't handle exit! error: ", e)


if __name__ == '__main__':
#    print('Im a working')
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--name", default=0, type=str, help='name of node like node102')
    argparser.add_argument("--port", default=8000, type=int, help='communication port for sending and listening messages')
    argparser.add_argument("--clusterNodes", nargs='+', default=[], type=str, help='nodes in the reserved cluster like node102 node103 node104')
    args = argparser.parse_args()

    default_state = "follower"

    cluster=[]

    for i,node in enumerate(args.clusterNodes):
        data={
             'name':node,
             'port':args.port+ i
            }
        cluster.append(data)


    # removing the current node from its cluster list
    cluster = [node for node in cluster if node['name'] != args.name]

    # **experimental** incrementing the port number based on index, separate ports for separate node

    port = args.port + args.clusterNodes.index(args.name)
 #   print(args.name)
    my_node = Node(args.name, default_state, port, cluster)
    try:
        print(f"Node {args.name} is starting", flush=True)
        my_node.start_loop_thread()
    except Exception as e:
        print("Exception", e)

    # exit handler *terminates threads and kills server
    atexit.register(my_node.handle_exit)
    signal.signal(signal.SIGTERM, my_node.handle_exit)
    signal.signal(signal.SIGINT, my_node.handle_exit)
