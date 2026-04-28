import re
import json
import argparse
import sys
import subprocess

def expand_slurm_nodes(node_str):
    """
    Expands Slurm's bracketed node notation into a list of strings.
    Example: 'cs-n[0000-0015]' -> ['cs-n0000', 'cs-n0001', ..., 'cs-n0015']
    """
    nodes = []
    match = re.search(r'([^[\]]+)\[([^[\]]+)\]', node_str)
    
    if match:
        prefix = match.group(1)
        ranges = match.group(2)
        
        for r in ranges.split(','):
            if '-' in r:
                start_str, end_str = r.split('-')
                width = len(start_str)
                for i in range(int(start_str), int(end_str) + 1):
                    nodes.append(f"{prefix}{str(i).zfill(width)}")
            else:
                nodes.append(f"{prefix}{r}")
    else:
        nodes.extend(node_str.split(','))
        
    return nodes

def get_slurm_cluster_name():
    try:
        # Compatible with older Python 3.6+ environments
        result = subprocess.run(['scontrol', 'show', 'config'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
        for line in result.stdout.split('\n'):
            if 'ClusterName' in line:
                return line.split('=')[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return "Unknown Slurm Cluster"

def parse_topo_file(filepath, racks_per_cabinet, nodes_per_blade, cpus, cores, system_name):
    switches = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if 'Level=0' in line:
                    name_match = re.search(r'SwitchName=(\S+)', line)
                    nodes_match = re.search(r'Nodes=(\S+)', line)
                    
                    if name_match and nodes_match:
                        switches.append({
                            "name": name_match.group(1),
                            "nodes": expand_slurm_nodes(nodes_match.group(1))
                        })
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}")
        sys.exit(1)

    return build_json_topology(switches, racks_per_cabinet, nodes_per_blade, cpus, cores, system_name)

def build_json_topology(switches, racks_per_cabinet, nodes_per_blade, cpus, cores, system_name):
    topology = {
        "metadata": {"system_name": system_name},
        "cabinets": []
    }
    
    # Tightened Spacing Modifiers
    cabinet_spacing_x = 60
    rack_spacing_x = 12
    blade_spacing_y = 12
    node_spacing_x = 8
    
    cab_idx = 0
    rack_idx = 0
    current_cabinet = None

    for switch in switches:
        if rack_idx % racks_per_cabinet == 0:
            if current_cabinet:
                topology["cabinets"].append(current_cabinet)
            
            current_cabinet = {
                "id": f"CAB-{cab_idx + 1:02d}",
                "x": cab_idx * cabinet_spacing_x,
                "z": 0,
                "racks": []
            }
            cab_idx += 1
            rack_idx = 0

        rack = {
            "id": f"RACK-{switch['name']}",
            "x_offset": rack_idx * rack_spacing_x,
            "z_offset": 0,
            "blades": [] # Upgraded to Blade architecture
        }
        
        # Chunk Slurm nodes into Blades
        current_blade = None
        
        for slot, hostname in enumerate(switch["nodes"]):
            blade_idx = slot // nodes_per_blade
            node_idx_in_blade = slot % nodes_per_blade

            # Initialize a new blade if the previous one is full
            if node_idx_in_blade == 0:
                current_blade = {
                    "id": f"BLADE-{switch['name']}-{blade_idx:02d}",
                    "y_offset": blade_idx * blade_spacing_y,
                    "nodes": []
                }
                rack["blades"].append(current_blade)
                
            current_blade["nodes"].append({
                "hostname": hostname,
                "slot": slot,
                "x_offset": node_idx_in_blade * node_spacing_x,
                "cpus": cpus,
                "cores_per_cpu": cores
            })
            
        current_cabinet["racks"].append(rack)
        rack_idx += 1

    if current_cabinet:
        topology["cabinets"].append(current_cabinet)

    return topology

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Slurm topo output to a JSON hardware map.")
    parser.add_argument("topo_file", type=str, help="Text file containing the output of 'scontrol show topo'")
    parser.add_argument("--system_name", type=str, default=None, help="Global name of the cluster.")
    
    # Topology arguments
    parser.add_argument("--racks_per_cab", type=int, default=4, help="How many switches/racks to group visually into one cabinet")
    parser.add_argument("--nodes_per_blade", type=int, default=4, help="How many nodes slide into a single blade")
    parser.add_argument("--cpus", type=int, default=2, help="Processors per node")
    parser.add_argument("--cores", type=int, default=32, help="Cores per processor")
    parser.add_argument("--out", type=str, default="hardware_map.json", help="Output filename")
    
    args = parser.parse_args()
    
    sys_name = args.system_name or get_slurm_cluster_name()
    
    final_topology = parse_topo_file(
        args.topo_file, 
        args.racks_per_cab, 
        args.nodes_per_blade, 
        args.cpus, 
        args.cores, 
        sys_name
    )
    
    with open(args.out, 'w') as f:
        json.dump(final_topology, f, indent=2)
        
    print(f"Map generated for '{sys_name}' with {sum(len(c['racks']) for c in final_topology['cabinets'])} switches.")
    print(f"Saved to {args.out}")
