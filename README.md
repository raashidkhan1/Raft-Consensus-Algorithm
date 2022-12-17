# DDPS-A2-Raft
Partial implementation of Raft consensus algorithm with focus on leader election performance

## How to run the implementation:
1. Login to DAS5
2. Reserve nodes
3. Clone the repository
4. Run the Node.py script from the root directory by updating the run.sh script with your user id
5. Additionally, the run.sh script might be needed to be enabled as an executable, use below command - 
```
chmod 777 ./run.sh
```
Additional scripts are provided to handle stopping server by cancelling the reservation and reserving immediately, this is a workaround to kill xmlrpc servers on DAS5.

To test the implementation with leader breakdown, uncomment the code for limited iterations and counter in [Node.py Line 237](https://github.com/raashidkhan1/DDPS-A2-Raft/blob/0c7d8567e7206c1bf8eca2158007d213a5a9ec41/Node.py#L237) and add the condition here [Node.py L85](https://github.com/raashidkhan1/DDPS-A2-Raft/blob/0c7d8567e7206c1bf8eca2158007d213a5a9ec41/Node.py#L85)

### Note: 
Infinite loop might cause the server to run indefinitely on the nodes, might be better to try out with limited iterations first.
