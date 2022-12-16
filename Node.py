import time
import random
import threading
import argparse
from xmlrpc.client import ServerProxy
from Server import Server
import atexit
import signal

##TODO : clean code and reorganize
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
        self.voted_for = None
        self.leader_node = ""
        self.online = True
        # all valid states
        self.states = ["leader", "follower", "candidate"]

        print(f"{self.node_name} says: Node initialized", flush=True)
        print(f"{self.node_name} says: Starting XMLRPC Server on node", self.node_name, flush=True)
        self.server = Server(self.node_name, self.port)
        self.server.register_function(self.message_received, "message_received")
        self.server.register_function(self.send_vote, "send_vote")
        self.server.start()
        print(f"{self.node_name} says: XMLRPCServer started", flush=True)


    ## basic functions
    def start_loop_thread(self):
        # infinite loops require a separate thread from main
        try:
            print(f"{self.node_name} says: loop thread started", flush=True)
            self.loop_thread = threading.Thread(target=self.node_self_loop())
            self.loop_thread.daemon = True # make it background
            self.loop_thread.start() ## self loop started in thread
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

            print(f"{self.node_name} says: requesting vote from:", node, flush=True)

            response = rpc_call.send_vote(self.term, self.node_name)

            if response:
                print(f"{self.node_name} says: got vote from {node}", flush=True)
                self.vote_count += 1.0
            else :
                print(f"{self.node_name} says: did not receive vote from {node}", flush=True)
                return

    def send_vote(self, term, candidate_node):
        ## Follower with term less than candidate and not voted yet
        if self.state == self.states[1] and self.term < term and self.voted_for == None:
            print(f"{self.node_name} says: voting for {candidate_node}", flush=True)
            self.voted_for = candidate_node
            return True
        ## Itself a candidate
        elif self.state == self.states[2]:
            print(f"{self.node_name} says: my state is {self.state}, not voting :P ", flush=True)
            return False
        ## already voted, election over
        elif self.voted_for != None:
            print(f"{self.node_name} says: to {candidate_node}- Already voted for {self.voted_for}", flush=True)
            return False
        ## ahead of candidate, election over
        elif self.term > term:
            print(f"{self.node_name} says: my term {self.term} is higher than your term {term}, election is over bro", flush=True)
            return False
        ## is a leader, offline
        elif not self.online: 
            print(f"{self.node_name} says: My state is {self.state} and online status is {self.online}, not voting for {candidate_node}", flush=True)
            return False

    # timer logic for
    def timer(self):
        return random.randrange(3, 8)

    def append_entries(self, node, port):
        with ServerProxy ('http://'+node+':'+ str(port)) as rpc_call:

            print(f"{self.node_name} says: Sending heartbeat to:",node, flush=True)

            response_term, response_leader_node = rpc_call.message_received(self.term, self.node_name)

            if response_term and response_leader_node:
                print(f"Leader {self.node_name} says: received response on heartbeats from {node} ", flush=True)
                if(self.term < response_term):
                    print(f"{self.node_name} says: I'm old leader, becoming follower", flush=True)
                    self.term = response_term
                    self.state = self.states[1]
                    if(self.leader_node != response_leader_node):
                        self.leader_node = response_leader_node
            else :
                print(f"{self.node_name} says: did not receive response on heartbeat from {node}", flush=True)
                return

    def message_received(self, term, leader_node):
        self.heartbeat_received = True
        print(f"{self.node_name} says: heartbeat received from {leader_node}", flush=True)
        # reset timer
        self.election_timeout = self.timer()

        self.voted_for = None

        if self.state == self.states[2] and self.leader_node != leader_node :
            print(f"{self.node_name} says: I was candidate, but leader {leader_node} is elected so becoming follower", flush=True)
            self.state = self.states[1]
            self.leader_node = leader_node
            self.term = term
            return term, self.leader_node
        elif self.term < term: 
            self.term = term
            self.leader_node = leader_node
            print(f"{self.node_name} says: update my own term from new leader {leader_node}", flush=True)            
            return term, self.leader_node
        elif self.term > term:
            print(f"{self.node_name} says: rejecting hearbeat from : ", leader_node, flush=True)
            return self.term, self.leader_node
        else:
            print(f"{self.node_name} says: I'm in sync with {leader_node}", flush=True)
            return term, self.leader_node


    ### functions for each type of node

    def leader(self):
        print(f"{self.node_name} says: I'm a leader man", flush=True)
        time.sleep(random.randrange(1,2))
        self.send_heartbeat()

    def candidate(self):
        print(f"{self.node_name} says: I'm a candidate man", flush=True)
        self.vote_count +=1
        previous_term = self.term
        self.term +=1
        all_request_threads = []
        self.voted_for = self.node_name
        # reset timer to not initiate another election
        self.election_timeout = self.timer()
        

        for node in self.cluster_nodes:
            thread = threading.Thread(target=self.request_vote, args=(node['name'], node['port']))
            thread.start()
            all_request_threads.append(thread)

        for t in all_request_threads:
            t.join()
        
        min_vote = float(0.5 * float(len(self.cluster_nodes)+1))

        ## check vote count
        if self.vote_count > min_vote:
            print(f"{self.node_name} says: Iam the leader now bitch", flush=True)
            self.state = self.states[0]
            self.vote_count = 0
            self.voted_for = None
            self.leader_node = self.node_name
        else:
            print(f"{self.node_name} says: failed to collect votes, becoming follower again", flush=True)
            self.state = self.states[1]
            self.term = previous_term
            self.voted_for = None
            self.vote_count = 0

    def follower(self):
        print(f"{self.node_name} says: I'm a follower man", flush=True)
        self.heartbeat_received = False
        time.sleep(self.election_timeout)
        print(f"{self.node_name} says: heartbeat from {self.leader_node} :", self.heartbeat_received, flush=True)
        if not self.heartbeat_received:
           self.state=self.states[2]


    def node_self_loop(self):
       #for testing only
        print(f"{self.node_name} says: starting my self loop", flush=True)
        count = 0
        # while(self.run_thread):
        for i in range(10):
            count +=1
            if self.state == self.states[0]:
                if(count == 5):
                    ## for testing leader breakdown
                    self.online = False
                    time.sleep(20)
                ## for testing leader breakdown    
                self.online = True
                self.leader()
            elif self.state == self.states[1]:
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
            print(f"{self.node_name} says: Node stopped", args.name, flush=True)
        except Exception as e:
            print(f"{self.node_name} says: Couldn't handle exit! error: ", e, flush=True)


if __name__ == '__main__':
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
    my_node = Node(args.name, default_state, port, cluster)
    try:
        print(f"Node {args.name} is starting", flush=True)
        my_node.start_loop_thread()
        ## experimental handle exit -- stop server
        # my_node.handle_exit()
    except Exception as e:
        print("Exception", e, flush=True)

    # exit handler *terminates threads and kills server
    atexit.register(my_node.handle_exit)
    signal.signal(signal.SIGTERM, my_node.handle_exit)
    signal.signal(signal.SIGINT, my_node.handle_exit)
