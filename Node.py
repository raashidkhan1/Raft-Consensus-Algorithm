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
        self.vote_count = 0

        # all valid states
        self.states = ["leader", "follower", "candidate"]

       #Experiment to check if port is active for rpc server not working
 #       sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 #       result = sock.connect_ex((self.node_name,self.port))


        print("Node initialized")
        print("Starting XMLRPC Server on node", self.node_name)
        self.server = Server(self.node_name, self.port)
        self.server.register_function(self.message_received, "message_received")
        self.server.register_function(self.send_vote, "send_vote")
        self.server.start()
        print("XMLRPCServer started")
#        sock.close()

        ##testing with node107 as leader
        # if self.node_name == "node107":
        #     self.state="leader"

        self.start_loop_thread()


    ## basic functions
    def start_loop_thread(self):
        # infinite loops require a separate thread from main
        self.loop_thread = threading.Thread(target=self.node_self_loop())
        self.loop_thread.daemon = True # make it background
        self.loop_thread.start() ## self loop started in thread
        print("loop thread started")
        while self.loop_thread.is_alive():
            self.loop_thread.join(1)

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

            print("requesting vote from:", node)

            response = rpc_call.send_vote(self.term)

            if response:
                print(f"Node, {node} sent vote")
                self.vote_count += 1
            else :
                print("Did not receive vote")
                return

    # timer logic for
    def timer(self):
        return random.randrange(1, 5)

    def append_entries(self, node, port):
        with ServerProxy ('http://'+node+':'+ str(port)) as rpc_call:

            print("Sending heartbeat to:",node)

            response = rpc_call.message_received(self.term)

            if response:
                print(f"Node, {node} received hearbeats")
                if(self.term < response):
                    self.term = response
                    self.state = self.states[1]
                    
            else :
                print("Did not receive")
                return

    def send_vote(self, term):
        if self.state != self.states[2] and self.term < term:
            return True
        else:
            print("Iam a candidate or your current term is low, no voting")
            return False

    def message_received(self, term):
        print("I'm node:", self.node_name)
        print("heartbeat received:", self.heartbeat_received)
        self.heartbeat_received = True
        if self.term < term: 
            self.term = term
            return term
        elif self.term > term:
            return self.term
        else:
            return term


    ### functions for each type of node

    def leader(self):
        print('Im a leader, bro!')
        self.send_heartbeat()

    def candidate(self):
        print('Im a candidate, bro!')
        self.vote_count +=1
        self.term +=1
        all_request_threads = []

        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.request_vote, args=(node['name'], node['port']))
            thread.start()
            all_request_threads.append(thread)

        for t in all_request_threads:
            t.join()
        
        ## check vote count
        if(self.vote_count >= len(self.cluster_nodes)/2):
            print(f"{self.node_name} says: Iam the leader now bitch")
            self.state = self.states[0]
            self.vote_count = 0
        else:
            print(f"{self.node_name} says: failed to collect votes, becoming follower again")
            self.state = self.states[1]
            self.vote_count = 0

    def follower(self):
        print('Im a follower, bro!')
        print("Follower message :", self.heartbeat_received)
        self.heartbeat_received = False
        time.sleep(self.election_timeout)
        ## check leader term and sync own term

        if not self.heartbeat_received:
           self.state=self.states[2]


    def node_self_loop(self):
       #for testing only
        print("FROM HOST:",self.node_name)
        for i in range(5):
            if self.state == self.states[0]:
                time.sleep(4)
                self.leader()
            elif self.state == self.states[1]:
                time.sleep(4)
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
#    print('Im a working')
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--name", default=0, type=str, help='name of node like node102')
    argparser.add_argument("--port", default=8000, type=int, help="communication port for sending and listening messages")
    argparser.add_argument("--clusterNodes", nargs='+', default=[], type=str, help="nodes in the reserved cluster like node102 node103 node104")
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
    try:
        my_node = Node(args.name, default_state, port, cluster)

    except KeyboardInterrupt:
        # my_node.handle_exit()
        pass
    except Exception as e:
        print("Exception", e)

    # exit handler *terminates threads and kills server
    atexit.register(my_node.handle_exit)
    signal.signal(signal.SIGTERM, my_node.handle_exit)
    signal.signal(signal.SIGINT, my_node.handle_exit)
