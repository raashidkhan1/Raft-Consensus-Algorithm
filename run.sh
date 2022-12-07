nodes=$(preserve -llist | grep ddps2204 | cut -f9)
read -r -a workers <<< "$nodes"

for node in "${workers[@]}"
do
  echo "" | ssh "$node" python3 $CODE/Node.py --name "$node" --port 8100 --clusterNodes "${workers[@]}" &
done

