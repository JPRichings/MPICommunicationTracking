import struct
import zlib
import json
import sys
import os

def extract_topology(mpix_filepath):
    if not os.path.exists(mpix_filepath):
        print(f"Error: File '{mpix_filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(mpix_filepath, "rb") as f:
        # 1. Read the first 4 bytes to get the compressed header size
        size_bytes = f.read(4)
        if len(size_bytes) < 4:
            print("Error: File is too small to be a valid mpix file.", file=sys.stderr)
            sys.exit(1)

        header_length = struct.unpack("<I", size_bytes)[0]
        
        # 2. Read only the compressed header block
        compressed_header = f.read(header_length)
        if len(compressed_header) < header_length:
            print("Error: Unexpected EOF while reading the header.", file=sys.stderr)
            sys.exit(1)

        # 3. Decompress and parse the JSON header
        try:
            header_json = zlib.decompress(compressed_header).decode("utf-8")
            header_data = json.loads(header_json)
        except Exception as e:
            print(f"Error decompressing or parsing header: {e}", file=sys.stderr)
            sys.exit(1)

        # 4. Extract the topology and blueprint
        topology_data = {
            "metadata": header_data.get("metadata", {}),
            "hardware_blueprint": header_data.get("hardware_blueprint", None),
            "topology": header_data.get("topology", [])
        }

        # 5. Output the extracted data as formatted JSON
        print(json.dumps(topology_data, indent=4))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_topology.py <filename.mpix>")
        sys.exit(1)

    extract_topology(sys.argv[1])
