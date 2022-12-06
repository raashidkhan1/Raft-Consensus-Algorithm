class Node :

    def __init__(self, name, state) -> None:
        pass

        self.node_name = name
        self.state = state

    ## basic functions

    # leader sends heartbeat to every node
    def send_heartbeat(self):
        pass

    # in case no hearbeat and timer ran out, self vote and request vote RPC
    def requestVote(self):
        pass

    # timer logic for 
    def timer(self):
        pass


    ### functions for each type of node

    def leader(self):
        pass

    def candidate(self):
        pass

    def follower(self):
        pass

    def node_self_loop(self, type):
        pass


if __name__ == '__main__':
    print('Im a working')