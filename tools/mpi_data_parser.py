import struct
import json
import sys
import os
import gzip
import zlib
import math
import gc
import numpy as np
from collections import defaultdict, Counter

# -----------------------------------------------------------------------------
# MPI Message Type Mapping
# -----------------------------------------------------------------------------

MESSAGE_TYPES = {
    13: "MPI_SEND",
    14: "MPI_RECV",
    15: "MPI_BSEND",
    16: "MPI_SSEND",
    17: "MPI_RSEND",
    18: "MPI_ISEND",
    19: "MPI_IBSEND",
    20: "MPI_ISSEND",
    21: "MPI_IRSEND",
    22: "MPI_IRECV",
    23: "MPI_SENDRECV",
    24: "MPI_WAIT",
    25: "MPI_WAITALL",
    26: "MPI_BARRIER",
    27: "MPI_BCAST",
    28: "MPI_REDUCE",
    29: "MPI_ALLREDUCE",
    30: "MPI_GATHER",
    31: "MPI_SCATTER",
    32: "MPI_ALLGATHER",
    33: "MPI_WAITANY",
    34: "MPI_WAITSOME",
    35: "MPI_TEST",
    36: "MPI_TESTANY",
    37: "MPI_TESTALL",
    38: "MPI_TESTSOME",
    39: "MPI_INIT",
    40: "MPI_FINALIZE",
}

MESSAGE_TYPE_ORDER = {name: code for code, name in MESSAGE_TYPES.items()}

SMALL_LABEL_TEXT = "P2P Small Type Messages"
LARGE_LABEL_TEXT = "P2P Large Type Messages"

MPIC_V2_MAGIC = b"MPICv002"
MPIC_V2_VERSION = 2

BINS = [
    "< 128B",
    "128B - 1KB",
    "1KB - 64KB",
    "64KB - 1MB",
    "1MB - 16MB",
    "> 16MB",
]

SEND_LIKE_CALLS = {
    "MPI_SEND", "MPI_BSEND", "MPI_SSEND", "MPI_RSEND",
    "MPI_ISEND", "MPI_IBSEND", "MPI_ISSEND", "MPI_IRSEND",
}

RECV_LIKE_CALLS = {
    "MPI_RECV", "MPI_IRECV",
}

COMPLETION_CALLS = {
    "MPI_WAIT", "MPI_WAITALL", "MPI_WAITANY", "MPI_WAITSOME",
    "MPI_TEST", "MPI_TESTANY", "MPI_TESTALL", "MPI_TESTSOME",
}

SYNC_CALLS = {
    "MPI_BARRIER", "MPI_INIT", "MPI_FINALIZE",
}

ROOTED_COLLECTIVES = {
    "MPI_BCAST", "MPI_REDUCE", "MPI_GATHER", "MPI_SCATTER",
}

GLOBAL_COLLECTIVES = {
    "MPI_ALLREDUCE", "MPI_ALLGATHER",
}

CATEGORY_MAP = {}
CATEGORY_NAMES = []

def get_category_id(cat_str):
    if cat_str not in CATEGORY_MAP:
        CATEGORY_MAP[cat_str] = len(CATEGORY_NAMES)
        CATEGORY_NAMES.append(cat_str)
    return CATEGORY_MAP[cat_str]

# -----------------------------------------------------------------------------
# Columnar Data Structure (reduced memory usage)
# -----------------------------------------------------------------------------

class ColumnarTimeline:
    def __init__(self):
        # Accumulate as pure Python lists (should be more efficient than dicts)
        self.local_time = []
        self.event_id = []
        self.rank_recording = []
        self.call = []
        self.comm = []
        self.tag = []
        self.sender = []
        self.receiver = []
        self.count = []
        self.bytes = []
        self.category = []
        self.synthetic_empty = []

    def finalize_to_numpy(self):
        # Convert lists to numpy arrays
        self.local_time = np.array(self.local_time, dtype=np.float64)
        self.event_id = np.array(self.event_id, dtype=np.int32)
        self.rank_recording = np.array(self.rank_recording, dtype=np.int32)
        self.call = np.array(self.call, dtype=np.int32)
        self.comm = np.array(self.comm, dtype=np.int64)
        self.tag = np.array(self.tag, dtype=np.int32)
        self.sender = np.array(self.sender, dtype=np.int32)
        self.receiver = np.array(self.receiver, dtype=np.int32)
        self.count = np.array(self.count, dtype=np.int32)
        self.bytes = np.array(self.bytes, dtype=np.int64)
        self.category = np.array(self.category, dtype=np.int16)
        self.synthetic_empty = np.array(self.synthetic_empty, dtype=np.bool_)
        
        self.time = self.local_time.copy()
        self.epoch_ns = np.zeros(len(self.local_time), dtype=np.int64)

    def sort_timeline(self):
        # Match original sort: epoch_ns (or inf), time, event_id, rank_recording
        sort_epoch = np.where(self.epoch_ns > 0, self.epoch_ns, np.iinfo(np.int64).max)
        
        # lexsort sorts by the last key provided first
        sort_idx = np.lexsort((self.rank_recording, self.event_id, self.time, sort_epoch))
        
        self.local_time = self.local_time[sort_idx]
        self.time = self.time[sort_idx]
        self.epoch_ns = self.epoch_ns[sort_idx]
        self.event_id = self.event_id[sort_idx]
        self.rank_recording = self.rank_recording[sort_idx]
        self.call = self.call[sort_idx]
        self.comm = self.comm[sort_idx]
        self.tag = self.tag[sort_idx]
        self.sender = self.sender[sort_idx]
        self.receiver = self.receiver[sort_idx]
        self.count = self.count[sort_idx]
        self.bytes = self.bytes[sort_idx]
        self.category = self.category[sort_idx]
        self.synthetic_empty = self.synthetic_empty[sort_idx]

    def __len__(self):
        return len(self.local_time)

    def generate_events(self):
        """Yields on-the-fly dictionary representations for the analysis phase"""
        for i in range(len(self)):
            yield {
                "local_time": float(self.local_time[i]),
                "time": float(self.time[i]),
                "epoch_ns": int(self.epoch_ns[i]) if self.epoch_ns[i] > 0 else None,
                "event_id": int(self.event_id[i]),
                "rank_recording": int(self.rank_recording[i]),
                "call": MESSAGE_TYPES.get(self.call[i], f"UNKNOWN_{self.call[i]}"),
                "comm": int(self.comm[i]),
                "tag": int(self.tag[i]),
                "sender": int(self.sender[i]),
                "receiver": int(self.receiver[i]),
                "count": int(self.count[i]),
                "bytes": int(self.bytes[i]),
                "category": CATEGORY_NAMES[self.category[i]],
                "synthetic_empty": bool(self.synthetic_empty[i]),
            }

# -----------------------------------------------------------------------------
# Binary layouts
# -----------------------------------------------------------------------------

PROCESS_INFO_FMT = "=iiii1024s"
PROCESS_INFO_SIZE = struct.calcsize(PROCESS_INFO_FMT)

PROCESS_TIME_ANCHOR_FMT = "=i4xdq"
PROCESS_TIME_ANCHOR_SIZE = struct.calcsize(PROCESS_TIME_ANCHOR_FMT)

P2P_SMALL_FMT = "=diiiiiiii"
P2P_SMALL_SIZE = struct.calcsize(P2P_SMALL_FMT)

P2P_LARGE_FMT = "=diiiiiiiiiiiii4x"
P2P_LARGE_SIZE = struct.calcsize(P2P_LARGE_FMT)

# -----------------------------------------------------------------------------
# Basic helpers
# -----------------------------------------------------------------------------

def _make_bins_template():
    return {
        "< 128B": 0,
        "128B - 1KB": 0,
        "1KB - 64KB": 0,
        "64KB - 1MB": 0,
        "1MB - 16MB": 0,
        "> 16MB": 0,
    }

def _cstr(raw_bytes):
    return raw_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")

def _open_maybe_gzip(filepath):
    with open(filepath, "rb") as probe:
        magic = probe.read(2)
    if filepath.endswith(".gz") or magic == b"\x1f\x8b":
        return gzip.open(filepath, "rb")
    return open(filepath, "rb")

def _read_exact(buffer, offset, size, context):
    end = offset + size
    if end > len(buffer):
        raise ValueError(f"Unexpected end of file while reading {context}: need {size} bytes at offset {offset}, only {len(buffer) - offset} remain")
    return buffer[offset:end], end

def _safe_div(num, den):
    return 0.0 if den == 0 else float(num) / float(den)

def _mean(values):
    return 0.0 if not values else float(sum(values)) / float(len(values))

def _pstdev(values):
    if not values: return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) * (x - m) for x in values) / float(len(values)))

def _cv(values):
    m = _mean(values)
    return 0.0 if m == 0.0 else _pstdev(values) / m

def _categorise_small_call(call_name):
    if call_name in COMPLETION_CALLS: return "completion"
    if call_name in SYNC_CALLS: return "synchronisation"
    if call_name in ("MPI_BCAST", "MPI_REDUCE", "MPI_ALLREDUCE"): return "collective"
    return "point-to-point"

def _categorise_large_part(call_name, part_index):
    if call_name == "MPI_SENDRECV": return f"sendrecv_part_{part_index}"
    return f"collective_part_{part_index}"

def _bin_for_bytes(num_bytes):
    if num_bytes < 0: return None
    if num_bytes < 128: return "< 128B"
    if num_bytes < 1024: return "128B - 1KB"
    if num_bytes < 65536: return "1KB - 64KB"
    if num_bytes < 1048576: return "64KB - 1MB"
    if num_bytes < 16777216: return "1MB - 16MB"
    return "> 16MB"

def _ensure_stats_entry(stats, call_name):
    if call_name not in stats:
        stats[call_name] = _make_bins_template()

def _update_stats(stats, call_name, bytes_vol):
    _ensure_stats_entry(stats, call_name)
    bucket = _bin_for_bytes(bytes_vol)
    if bucket is not None:
        stats[call_name][bucket] += 1

def _severity(score):
    if score >= 0.85: return "critical"
    if score >= 0.6: return "warning"
    return "info"

def print_progress(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='#'):
    if total == 0: return
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total: print()

# -----------------------------------------------------------------------------
# Timeline recording helpers
# -----------------------------------------------------------------------------

def _record_small_event(timeline, stats, rank_id, local_time, msg_id, mtype, comm, tag, sender, receiver, count, bytes_vol):
    timeline.local_time.append(local_time)
    timeline.event_id.append(msg_id)
    timeline.rank_recording.append(rank_id)
    timeline.call.append(mtype)
    timeline.comm.append(comm)
    timeline.tag.append(tag)
    timeline.sender.append(sender)
    timeline.receiver.append(receiver)
    timeline.count.append(count)
    timeline.bytes.append(bytes_vol)
    
    call_name = MESSAGE_TYPES.get(mtype, f"UNKNOWN_{mtype}")
    timeline.category.append(get_category_id(_categorise_small_call(call_name)))
    timeline.synthetic_empty.append(False)
    
    _update_stats(stats, call_name, bytes_vol)

def _record_large_event(timeline, stats, rank_id, local_time, msg_id, mtype, comm, s1, r1, c1, b1, t1, s2, r2, c2, b2, t2):
    call_name = MESSAGE_TYPES.get(mtype, f"UNKNOWN_{mtype}")
    _ensure_stats_entry(stats, call_name)

    parts = [(1, s1, r1, c1, b1, t1), (2, s2, r2, c2, b2, t2)]

    for part_index, sender, receiver, count, bytes_vol, tag in parts:
        is_empty_placeholder = (count <= 0 and bytes_vol <= 0)
        
        timeline.local_time.append(local_time)
        timeline.event_id.append(msg_id)
        timeline.rank_recording.append(rank_id)
        timeline.call.append(mtype)
        timeline.comm.append(comm)
        timeline.tag.append(tag)
        timeline.sender.append(sender)
        timeline.receiver.append(receiver)
        timeline.count.append(count)
        timeline.bytes.append(bytes_vol)
        timeline.category.append(get_category_id(_categorise_large_part(call_name, part_index)))
        timeline.synthetic_empty.append(bool(is_empty_placeholder))

        if not is_empty_placeholder:
            _update_stats(stats, call_name, bytes_vol)

# -----------------------------------------------------------------------------
# Hardware map
# -----------------------------------------------------------------------------

def load_hardware_map(filepath):
    if not filepath or not os.path.exists(filepath):
        return {}

    with open(filepath, "r") as f:
        hw = json.load(f)

    lookup = {}
    for cab in hw.get("cabinets", []):
        cab_id, cab_x, cab_z = cab.get("id"), cab.get("x", 0), cab.get("z", 0)
        for rack in cab.get("racks", []):
            rack_id, rack_x_off, rack_z_off = rack.get("id"), rack.get("x_offset", 0), rack.get("z_offset", 0)
            if "blades" in rack:
                for blade in rack.get("blades", []):
                    blade_id, blade_y_off = blade.get("id"), blade.get("y_offset", 0)
                    for node in blade.get("nodes", []):
                        if hostname := node.get("hostname"):
                            lookup[hostname] = {
                                "cab_id": cab_id, "rack_id": rack_id, "blade_id": blade_id,
                                "x": cab_x + rack_x_off + node.get("x_offset", node.get("slot", 0) * 12),
                                "y": blade_y_off, "z": cab_z + rack_z_off,
                            }
            else:
                for node in rack.get("nodes", []):
                    if hostname := node.get("hostname"):
                        lookup[hostname] = {
                            "cab_id": cab_id, "rack_id": rack_id,
                            "x": cab_x + rack_x_off, "y": node.get("slot", 0) * 15, "z": cab_z + rack_z_off,
                        }
    return lookup

# -----------------------------------------------------------------------------
# Header parsing
# -----------------------------------------------------------------------------

def _make_topology_entry(rank, pid, core, chip, hostname, hw_lookup, anchor=None):
    hw_info = hw_lookup.get(hostname, {"x": rank * 15, "y": 0, "z": 0, "cab_id": None, "rack_id": None, "blade_id": None})
    topo_entry = {
        "rank": rank, "pid": pid, "core": core, "chip": chip, "hostname": hostname,
        "x": hw_info.get("x", rank * 15), "y": hw_info.get("y", 0), "z": hw_info.get("z", 0),
    }
    for key in ["cab_id", "rack_id", "blade_id"]:
        if key in hw_info: topo_entry[key] = hw_info.get(key)
    if anchor is not None:
        topo_entry["mpi_time_zero"] = anchor["mpi_time_zero"]
        topo_entry["unix_time_zero_ns"] = anchor["unix_time_zero_ns"]
    return topo_entry

def _parse_v2_header(raw_bytes, hw_lookup):
    offset = 0
    magic, offset = _read_exact(raw_bytes, offset, 8, "v2 magic")
    if magic != MPIC_V2_MAGIC: raise ValueError("Not a MPICv002 file")

    chunk, offset = _read_exact(raw_bytes, offset, 4, "v2 format version")
    version = struct.unpack("=I", chunk)[0]
    if version != MPIC_V2_VERSION: raise ValueError(f"Unsupported MPIC format version {version}")

    chunk, offset = _read_exact(raw_bytes, offset, 4, "world size")
    total_ranks = struct.unpack("=i", chunk)[0]
    if total_ranks < 0: raise ValueError(f"Invalid world size {total_ranks}")

    chunk, offset = _read_exact(raw_bytes, offset, 64, "date")
    run_date = _cstr(chunk)

    chunk, offset = _read_exact(raw_bytes, offset, 1024, "program")
    prog_name = _cstr(chunk)

    processes = []
    for idx in range(total_ranks):
        chunk, offset = _read_exact(raw_bytes, offset, PROCESS_INFO_SIZE, f"process info {idx}")
        rank, pid, core, chip, hostname_b = struct.unpack(PROCESS_INFO_FMT, chunk)
        processes.append({"rank": rank, "pid": pid, "core": core, "chip": chip, "hostname": _cstr(hostname_b)})

    anchors = [None] * total_ranks
    for idx in range(total_ranks):
        chunk, offset = _read_exact(raw_bytes, offset, PROCESS_TIME_ANCHOR_SIZE, f"time anchor {idx}")
        rank, mpi_time_zero, unix_time_zero_ns = struct.unpack(PROCESS_TIME_ANCHOR_FMT, chunk)
        target_idx = rank if 0 <= rank < total_ranks else idx
        anchors[target_idx] = {"rank": rank, "mpi_time_zero": mpi_time_zero, "unix_time_zero_ns": unix_time_zero_ns}

    topology = [_make_topology_entry(p["rank"], p["pid"], p["core"], p["chip"], p["hostname"], hw_lookup, anchors[p["rank"]] if 0 <= p["rank"] < total_ranks else None) for p in processes]

    metadata = {
        "total_ranks": total_ranks, "date": run_date, "program": prog_name if prog_name else "unknown",
        "system_name": "Unknown Cluster", "file_format": "MPICv002", "file_format_version": version,
        "time_registration": "per-rank-unix-anchor",
    }
    return metadata, topology, anchors, offset

def _parse_v1_header(raw_bytes, hw_lookup):
    offset = 0
    global_header_fmt = "=i64s1024s"
    global_header_size = struct.calcsize(global_header_fmt)

    chunk, offset = _read_exact(raw_bytes, offset, global_header_size, "legacy global header")
    total_ranks, raw_date, raw_prog = struct.unpack(global_header_fmt, chunk)
    if total_ranks < 0: raise ValueError(f"Invalid legacy world size {total_ranks}")

    topology = []
    for idx in range(total_ranks):
        chunk, offset = _read_exact(raw_bytes, offset, PROCESS_INFO_SIZE, f"legacy process info {idx}")
        rank, pid, core, chip, hostname_b = struct.unpack(PROCESS_INFO_FMT, chunk)
        topology.append(_make_topology_entry(rank, pid, core, chip, _cstr(hostname_b), hw_lookup, None))

    metadata = {
        "total_ranks": total_ranks, "date": _cstr(raw_date), "program": _cstr(raw_prog) if raw_prog else "unknown",
        "system_name": "Unknown Cluster", "file_format": "legacy-v1", "file_format_version": 1,
        "time_registration": "legacy-local-time",
    }
    return metadata, topology, [None] * total_ranks, offset

def _parse_mpic_header(raw_bytes, hw_lookup):
    if len(raw_bytes) >= 8 and raw_bytes[:8] == MPIC_V2_MAGIC:
        return _parse_v2_header(raw_bytes, hw_lookup)
    return _parse_v1_header(raw_bytes, hw_lookup)

# -----------------------------------------------------------------------------
# Section parsing
# -----------------------------------------------------------------------------

def _parse_sections_strict(raw_data, total_ranks, data):
    offset = 0
    tl = data["timeline"]
    stats = data["statistics"]

    for section_index in range(total_ranks):
        chunk, offset = _read_exact(raw_data, offset, 4, "rank id")
        rank_id = struct.unpack("=i", chunk)[0]

        chunk, offset = _read_exact(raw_data, offset, 24, "small section label")
        small_label = _cstr(chunk)
        if small_label != SMALL_LABEL_TEXT: raise ValueError(f"Bad small-section label for rank {rank_id}: {small_label!r}")

        chunk, offset = _read_exact(raw_data, offset, 4, "small section count")
        num_small = struct.unpack("=i", chunk)[0]
        if num_small < 0: raise ValueError(f"Negative small record count {num_small} for rank {rank_id}")

        for _ in range(num_small):
            chunk, offset = _read_exact(raw_data, offset, P2P_SMALL_SIZE, "small record")
            _record_small_event(tl, stats, rank_id, *struct.unpack(P2P_SMALL_FMT, chunk))

        chunk, offset = _read_exact(raw_data, offset, 24, "large section label")
        large_label = _cstr(chunk)
        if large_label != LARGE_LABEL_TEXT: raise ValueError(f"Bad large-section label for rank {rank_id}: {large_label!r}")

        chunk, offset = _read_exact(raw_data, offset, 4, "large section count")
        num_large = struct.unpack("=i", chunk)[0]
        if num_large < 0: raise ValueError(f"Negative large record count {num_large} for rank {rank_id}")

        for _ in range(num_large):
            chunk, offset = _read_exact(raw_data, offset, P2P_LARGE_SIZE, "large record")
            _record_large_event(tl, stats, rank_id, *struct.unpack(P2P_LARGE_FMT, chunk))

        print_progress(section_index + 1, total_ranks, prefix='Parsing Ranks:', suffix='Complete', length=40)

    if offset < len(raw_data) and any(b != 0 for b in raw_data[offset:]):
        raise ValueError("Unexpected non-zero trailing bytes after strict parse")

def _parse_sections_salvage(raw_data, total_len, data):
    offset = 0
    parsed_sections = 0
    seen_ranks = set()
    tl = data["timeline"]
    stats = data["statistics"]

    print("Running salvage parser...")
    while offset + 32 <= total_len:
        rank_bytes, label_bytes = raw_data[offset:offset + 4], raw_data[offset + 4:offset + 28]
        if len(rank_bytes) < 4 or len(label_bytes) < 24: break

        rank_id = struct.unpack("=i", rank_bytes)[0]
        if _cstr(label_bytes) != SMALL_LABEL_TEXT:
            offset += 1; continue

        try:
            num_small = struct.unpack("=i", raw_data[offset + 28:offset + 32])[0]
        except struct.error:
            offset += 1; continue

        if num_small < 0: offset += 1; continue

        small_bytes_end = offset + 32 + num_small * P2P_SMALL_SIZE
        if small_bytes_end + 28 > total_len or _cstr(raw_data[small_bytes_end:small_bytes_end + 24]) != LARGE_LABEL_TEXT:
            offset += 1; continue

        try:
            num_large = struct.unpack("=i", raw_data[small_bytes_end + 24:small_bytes_end + 28])[0]
        except struct.error:
            offset += 1; continue

        if num_large < 0: offset += 1; continue

        section_end = small_bytes_end + 28 + num_large * P2P_LARGE_SIZE
        if section_end > total_len or rank_id in seen_ranks:
            offset += 1; continue

        local_offset = offset + 32
        for _ in range(num_small):
            _record_small_event(tl, stats, rank_id, *struct.unpack(P2P_SMALL_FMT, raw_data[local_offset:local_offset + P2P_SMALL_SIZE]))
            local_offset += P2P_SMALL_SIZE

        local_offset = small_bytes_end + 28
        for _ in range(num_large):
            _record_large_event(tl, stats, rank_id, *struct.unpack(P2P_LARGE_FMT, raw_data[local_offset:local_offset + P2P_LARGE_SIZE]))
            local_offset += P2P_LARGE_SIZE

        seen_ranks.add(rank_id)
        parsed_sections += 1
        offset = section_end
        print_progress(offset, total_len, prefix='Salvaging:   ', suffix='Complete', length=40)

    print_progress(total_len, total_len, prefix='Salvaging:   ', suffix='Complete', length=40)
    if parsed_sections == 0: raise ValueError("Salvage parser found no valid rank sections")
    if parsed_sections < data["metadata"].get("total_ranks", 0):
        print(f"Warning: salvage parser recovered {parsed_sections} / {data['metadata'].get('total_ranks', 0)} rank sections", file=sys.stderr)

# -----------------------------------------------------------------------------
# Time registration 
# -----------------------------------------------------------------------------

def _apply_time_registration(data):
    anchors = data.get("time_anchors", [])
    tl = data["timeline"]

    valid_anchor_epochs = [a["unix_time_zero_ns"] for a in anchors if a and a.get("unix_time_zero_ns", 0) > 0]

    if not valid_anchor_epochs:
        data["metadata"]["timeline_clock"] = "local-relative"
        data["metadata"]["timeline_origin"] = "as-recorded"
        return

    global_origin_ns = min(valid_anchor_epochs)
    
    epoch_bases = np.zeros(len(anchors), dtype=np.int64)
    for i, a in enumerate(anchors):
        if a and a.get("unix_time_zero_ns", 0) > 0:
            epoch_bases[i] = a["unix_time_zero_ns"]

    valid_mask = epoch_bases[tl.rank_recording] > 0
    
    tl.epoch_ns[valid_mask] = epoch_bases[tl.rank_recording][valid_mask] + (tl.local_time[valid_mask] * 1.0e9).astype(np.int64)
    tl.time[valid_mask] = (tl.epoch_ns[valid_mask] - global_origin_ns) / 1.0e9

    data["metadata"]["timeline_clock"] = "global-epoch-registered"
    data["metadata"]["timeline_origin_unix_ns"] = global_origin_ns
    data["metadata"]["timeline_origin"] = "minimum-rank-anchor"

# -----------------------------------------------------------------------------
# Human-readable summaries
# -----------------------------------------------------------------------------

def print_summary_table(stats, total_ranks):
    print("\n" + "=" * 115) 
    print(f" MPI COMMUNICATION SUMMARY ({total_ranks} Ranks)")
    print("=" * 115)

    if not stats:
        print(" No communication events found.")
        print("=" * 115 + "\n")
        return

    ordered_calls = sorted(stats.keys(), key=lambda name: MESSAGE_TYPE_ORDER.get(name, 9999))
    header = " {:<13} | ".format("MPI Call") + " | ".join("{:<10}".format(b) for b in BINS) + " | {:<8} | {:<12}".format("Total", "Per-Rank Avg")
    print(header)
    print("-" * len(header))

    for call in ordered_calls:
        bin_data = stats[call]
        short_call = call.replace("MPI_", "")
        row = " {:<13} | ".format(short_call)
        total = 0
        for bucket in BINS:
            count = bin_data.get(bucket, 0)
            total += count
            row += "{:<10} | ".format(count)
            
        avg = total / total_ranks if total_ranks > 0 else 0
        row += "{:<8} | {:<12.1f}".format(total, avg)
        print(row)

    print("=" * 115 + "\n")

def print_analysis_summary(analysis, total_ranks):
    print("\n" + "=" * 95)
    print(f" TRACE ANALYSIS SUMMARY ({total_ranks} Ranks)")
    print("=" * 95)

    summary = analysis.get("summary", {})
    tot_events = summary.get('total_events', 0)
    can_events = summary.get('canonical_transfer_events', 0)
    comp_events = summary.get('completion_events', 0)
    bar_events = summary.get('barrier_events', 0)
    
    avg_events = tot_events / total_ranks if total_ranks > 0 else 0
    avg_can = can_events / total_ranks if total_ranks > 0 else 0
    avg_comp = comp_events / total_ranks if total_ranks > 0 else 0
    avg_bar = bar_events / total_ranks if total_ranks > 0 else 0

    print(f" Total events:              {tot_events:<15} (Avg per rank: {avg_events:.1f})")
    print(f" Canonical transfers:       {can_events:<15} (Avg per rank: {avg_can:.1f})")
    print(f" Canonical transfer bytes:  {summary.get('canonical_transfer_bytes', 0):<15}")
    print(f" Completion events:         {comp_events:<15} (Avg per rank: {avg_comp:.1f})")
    print(f" Barrier events:            {bar_events:<15} (Avg per rank: {avg_bar:.1f})")
    print(f" Estimated runtime:         {summary.get('estimated_runtime', 0.0):.6f}s")

    patterns = analysis.get("patterns", [])
    issues = analysis.get("issues", [])

    if patterns:
        print("\n Detected Patterns:")
        for pat in patterns: print(f"  - [{pat.get('type', 'pattern')}] {pat.get('description', '')}")

    if issues:
        print("\n Potential Performance Issues:")
        for issue in issues: print(f"  - [{issue.get('severity', 'info').upper()}] {issue.get('description', '')}")

    print("=" * 95 + "\n")

# -----------------------------------------------------------------------------
# Analysis helpers
# -----------------------------------------------------------------------------

def _is_real_payload_event(event):
    return (event.get("bytes", 0) > 0) and (not event.get("synthetic_empty", False))

def _is_canonical_transfer_event(event):
    if not _is_real_payload_event(event): return False
    call = event["call"]
    category = event.get("category", "")
    if call in SEND_LIKE_CALLS: return True
    if call == "MPI_SENDRECV" and category == "sendrecv_part_1": return True
    if call == "MPI_BCAST" and event["sender"] != event["receiver"]: return True
    if call == "MPI_REDUCE" and event["sender"] != event["receiver"]: return True
    if call == "MPI_GATHER" and category == "collective_part_1" and event["sender"] != event["receiver"]: return True
    if call == "MPI_SCATTER" and category == "collective_part_2" and event["sender"] != event["receiver"]: return True
    return False

def _guess_root_for_rooted_collective(event):
    call = event["call"]
    if call in ("MPI_BCAST", "MPI_SCATTER"): return event["sender"]
    if call in ("MPI_REDUCE", "MPI_GATHER"): return event["receiver"]
    return None

def _build_time_windows(events_generator, total_events, window_count, runtime, start_t):
    if total_events == 0: return []
    windows = [{"t_start": start_t + (runtime * i) / float(window_count), "t_end": start_t + (runtime * (i + 1)) / float(window_count), "events": 0, "canonical_transfer_events": 0, "canonical_transfer_bytes": 0, "completion_events": 0, "barrier_events": 0, "collective_events": 0} for i in range(window_count)]
    for event in events_generator:
        idx = 0 if runtime <= 0.0 else min(window_count - 1, max(0, int(((event["time"] - start_t) / runtime) * window_count)))
        win = windows[idx]
        win["events"] += 1
        if _is_canonical_transfer_event(event):
            win["canonical_transfer_events"] += 1
            win["canonical_transfer_bytes"] += event.get("bytes", 0)
        if event["call"] in COMPLETION_CALLS: win["completion_events"] += 1
        if event["call"] == "MPI_BARRIER": win["barrier_events"] += 1
        if event["call"] in ROOTED_COLLECTIVES or event["call"] in GLOBAL_COLLECTIVES: win["collective_events"] += 1
    return windows

def analyse_trace(data):
    timeline_obj = data["timeline"]
    total_ranks = data["metadata"].get("total_ranks", 0)
    total_events = len(timeline_obj)

    per_rank = {r: {"rank": r, "events": 0, "completion_events": 0, "barrier_events": 0, "collective_events": 0, "global_collective_events": 0, "rooted_collective_events": 0, "canonical_bytes_out": 0, "canonical_bytes_in": 0, "canonical_messages_out": 0, "canonical_messages_in": 0, "distinct_out_peers": set(), "distinct_in_peers": set(), "completion_request_count": 0} for r in range(total_ranks)}
    pair_stats = defaultdict(lambda: {"messages": 0, "bytes": 0, "calls": Counter(), "first_time": None, "last_time": None, "comm": None, "sender": None, "receiver": None})
    rooted_collective_roots = defaultdict(lambda: {"events": 0, "bytes": 0, "calls": Counter()})
    barrier_times = defaultdict(list)

    canonical_total_events, canonical_total_bytes, completion_total_events, barrier_total_events, collective_total_events, global_collective_total_events = 0, 0, 0, 0, 0, 0
    small_by_call, small128_by_call, small1k_by_call = Counter(), Counter(), Counter()

    start_t = timeline_obj.time[0] if total_events > 0 else 0.0
    end_t = timeline_obj.time[-1] if total_events > 0 else 0.0
    runtime = max(0.0, end_t - start_t)

    print("\nAnalyzing Trace...")
    for idx, event in enumerate(timeline_obj.generate_events()):
        rr = event["rank_recording"]
        call = event["call"]
        t = event["time"]
        comm = event.get("comm", 0)
        tag = event.get("tag", 0)
        sender = event["sender"]
        receiver = event["receiver"]
        num_bytes = event.get("bytes", 0)

        # Basic counts
        if rr in per_rank:
            per_rank[rr]["events"] += 1
            if call in COMPLETION_CALLS:
                per_rank[rr]["completion_events"] += 1
                per_rank[rr]["completion_request_count"] += max(0, event.get("count", 0))
            if call == "MPI_BARRIER":
                per_rank[rr]["barrier_events"] += 1
                barrier_times[rr].append(t)
            if call in ROOTED_COLLECTIVES or call in GLOBAL_COLLECTIVES:
                per_rank[rr]["collective_events"] += 1
                if call in ROOTED_COLLECTIVES: per_rank[rr]["rooted_collective_events"] += 1
                if call in GLOBAL_COLLECTIVES: per_rank[rr]["global_collective_events"] += 1

        if call in COMPLETION_CALLS: completion_total_events += 1
        if call == "MPI_BARRIER": barrier_total_events += 1
        if call in ROOTED_COLLECTIVES or call in GLOBAL_COLLECTIVES: collective_total_events += 1
        if call in GLOBAL_COLLECTIVES: global_collective_total_events += 1

        # Canonical traffic
        if _is_canonical_transfer_event(event):
            canonical_total_events += 1
            canonical_total_bytes += num_bytes

            if 0 <= sender < total_ranks:
                per_rank[sender]["canonical_bytes_out"] += num_bytes
                per_rank[sender]["canonical_messages_out"] += 1
                per_rank[sender]["distinct_out_peers"].add(receiver)

            if 0 <= receiver < total_ranks:
                per_rank[receiver]["canonical_bytes_in"] += num_bytes
                per_rank[receiver]["canonical_messages_in"] += 1
                per_rank[receiver]["distinct_in_peers"].add(sender)

            pair_key = (comm, sender, receiver)
            ps = pair_stats[pair_key]
            ps["messages"] += 1
            ps["bytes"] += num_bytes
            ps["calls"][call] += 1
            ps["comm"], ps["sender"], ps["receiver"] = comm, sender, receiver
            if ps["first_time"] is None or t < ps["first_time"]: ps["first_time"] = t
            if ps["last_time"] is None or t > ps["last_time"]: ps["last_time"] = t

            small_by_call[call] += 1
            if num_bytes < 128: small128_by_call[call] += 1
            if num_bytes < 1024: small1k_by_call[call] += 1

            if call in ROOTED_COLLECTIVES:
                if (root := _guess_root_for_rooted_collective(event)) is not None:
                    rooted_collective_roots[root]["events"] += 1
                    rooted_collective_roots[root]["bytes"] += num_bytes
                    rooted_collective_roots[root]["calls"][call] += 1

        if idx % 20000 == 0:
            print_progress(idx, total_events, prefix='Processing: ', suffix='Complete', length=40, fill='#')
    print_progress(total_events, total_events, prefix='Processing: ', suffix='Complete', length=40, fill='#')

    # Aggregation
    per_rank_list, total_touch_bytes, out_peer_counts, in_peer_counts = [], [], [], []
    for rank in range(total_ranks):
        entry = per_rank[rank]
        entry["distinct_out_peers"] = len(entry["distinct_out_peers"])
        entry["distinct_in_peers"] = len(entry["distinct_in_peers"])
        entry["touch_bytes"] = entry["canonical_bytes_out"] + entry["canonical_bytes_in"]
        per_rank_list.append(entry)
        total_touch_bytes.append(entry["touch_bytes"])
        out_peer_counts.append(entry["distinct_out_peers"])
        in_peer_counts.append(entry["distinct_in_peers"])

    top_links = [{"comm": s["comm"], "sender": s["sender"], "receiver": s["receiver"], "messages": s["messages"], "bytes": s["bytes"], "calls": dict(sorted(s["calls"].items())), "first_time": s["first_time"], "last_time": s["last_time"]} for _k, s in sorted(pair_stats.items(), key=lambda kv: kv[1]["bytes"], reverse=True)[:20]]
    top_ranks_by_out = [{"rank": r["rank"], "bytes": r["canonical_bytes_out"], "messages": r["canonical_messages_out"]} for r in sorted(per_rank_list, key=lambda x: x["canonical_bytes_out"], reverse=True)[:10]]
    top_ranks_by_in = [{"rank": r["rank"], "bytes": r["canonical_bytes_in"], "messages": r["canonical_messages_in"]} for r in sorted(per_rank_list, key=lambda x: x["canonical_bytes_in"], reverse=True)[:10]]
    top_ranks_by_touch = [{"rank": r["rank"], "bytes": r["touch_bytes"]} for r in sorted(per_rank_list, key=lambda x: x["touch_bytes"], reverse=True)[:10]]
    rooted_collective_summary = [{"root": r, "events": s["events"], "bytes": s["bytes"], "calls": dict(sorted(s["calls"].items()))} for r, s in sorted(rooted_collective_roots.items(), key=lambda kv: kv[1]["bytes"], reverse=True)]
    
    barrier_spreads = []
    if total_ranks > 0:
        barrier_counts = [len(barrier_times[r]) for r in range(total_ranks)]
        for idx in range(min(barrier_counts) if barrier_counts else 0):
            times = [barrier_times[r][idx] for r in range(total_ranks)]
            barrier_spreads.append({"barrier_index": idx, "t_min": min(times), "t_max": max(times), "spread": max(times) - min(times)})

    avg_out_peers = _mean(out_peer_counts)
    avg_in_peers = _mean(in_peer_counts)
    pair_density = _safe_div(len(pair_stats), total_ranks * max(0, total_ranks - 1))
    touch_cv = _cv(total_touch_bytes)
    top_link_share = _safe_div(top_links[0]["bytes"], canonical_total_bytes) if top_links and canonical_total_bytes > 0 else 0.0
    small1k_total = sum(small1k_by_call.values())
    small1k_ratio = _safe_div(small1k_total, canonical_total_events)
    rooted_total_bytes = sum(r["bytes"] for r in rooted_collective_summary)
    top_root_share = _safe_div(rooted_collective_summary[0]["bytes"], rooted_total_bytes) if rooted_collective_summary and rooted_total_bytes > 0 else 0.0
    completion_to_transfer_ratio = _safe_div(completion_total_events, canonical_total_events)
    max_barrier_spread = max((b["spread"] for b in barrier_spreads), default=0.0)
    avg_barrier_spread = _mean([b["spread"] for b in barrier_spreads]) if barrier_spreads else 0.0

    # Patterns
    patterns = []
    if pair_density >= 0.5 and total_ranks >= 8: patterns.append({"type": "dense-communication", "description": f"Communication graph is dense (pair density {pair_density:.3f}).", "metrics": {"pair_density": pair_density, "pairs_observed": len(pair_stats)}})
    elif 0.0 < pair_density <= 0.1 and total_ranks >= 8: patterns.append({"type": "sparse-communication", "description": f"Communication graph is sparse (pair density {pair_density:.3f}).", "metrics": {"pair_density": pair_density, "pairs_observed": len(pair_stats)}})
    if small1k_ratio >= 0.5 and canonical_total_events > 0: patterns.append({"type": "small-message-dominated", "description": f"A large fraction of canonical transfers are under 1KB ({small1k_ratio:.1%}).", "metrics": {"small_lt_1kb_ratio": small1k_ratio, "small_lt_1kb_events": small1k_total}})
    if rooted_collective_summary and top_root_share >= 0.5: patterns.append({"type": "root-concentrated-collectives", "description": f"One rank dominates rooted collective traffic ({top_root_share:.1%} bytes).", "metrics": {"top_root": rooted_collective_summary[0]["root"], "top_root_share": top_root_share}})
    if top_link_share >= 0.2 and canonical_total_bytes > 0: patterns.append({"type": "dominant-link", "description": f"A single link carries {top_link_share:.1%} of canonical traffic.", "metrics": {"top_link_share": top_link_share, "top_link": top_links[0] if top_links else None}})
    if touch_cv >= 1.0 and total_ranks > 1: patterns.append({"type": "rank-communication-imbalance", "description": f"Communication volume per rank is imbalanced (CV {touch_cv:.3f}).", "metrics": {"touch_bytes_cv": touch_cv}})
    if completion_to_transfer_ratio >= 0.5: patterns.append({"type": "completion-heavy", "description": f"Completion calls are frequent relative to canonical transfers ({completion_to_transfer_ratio:.3f}).", "metrics": {"completion_to_transfer_ratio": completion_to_transfer_ratio}})
    if barrier_total_events > 0 and _safe_div(barrier_total_events, total_events) >= 0.05: patterns.append({"type": "barrier-heavy", "description": f"Barrier usage is prominent ({barrier_total_events} events).", "metrics": {"barrier_events": barrier_total_events, "barrier_fraction": _safe_div(barrier_total_events, total_events)}})

    # Issues
    issues = []
    if small1k_ratio >= 0.6 and canonical_total_events > 0:
        score = min(small1k_ratio, 1.0)
        issues.append({"type": "small_message_pressure", "severity": _severity(score), "score": score, "description": f"High fraction of canonical traffic uses small payloads (<1KB: {small1k_ratio:.1%}).", "metrics": {"small_lt_1kb_ratio": small1k_ratio}})
    if touch_cv >= 1.2 and total_ranks > 1:
        score = min(touch_cv / 2.0, 1.0)
        issues.append({"type": "rank_traffic_imbalance", "severity": _severity(score), "score": score, "description": f"Per-rank volume is strongly imbalanced (CV {touch_cv:.3f}).", "metrics": {"touch_bytes_cv": touch_cv}})
    if top_root_share >= 0.7 and rooted_total_bytes > 0:
        score = min(top_root_share, 1.0)
        issues.append({"type": "collective_root_bottleneck", "severity": _severity(score), "score": score, "description": f"One root rank accounts for {top_root_share:.1%} of rooted collective bytes.", "metrics": {"top_root_share": top_root_share}})
    if barrier_spreads and runtime > 0.0:
        rel_barrier_spread = _safe_div(max_barrier_spread, runtime)
        if max_barrier_spread >= 0.001 and rel_barrier_spread >= 0.01:
            score = min(rel_barrier_spread * 5.0, 1.0)
            issues.append({"type": "barrier_arrival_skew", "severity": _severity(score), "score": score, "description": f"Barriers exhibit skew (max spread {max_barrier_spread:.6f}s).", "metrics": {"max_barrier_spread": max_barrier_spread}})
    if completion_to_transfer_ratio >= 1.0 and completion_total_events > 0:
        score = min(completion_to_transfer_ratio / 2.0, 1.0)
        issues.append({"type": "completion_overhead", "severity": _severity(score), "score": score, "description": f"Completion calls highly frequent relative to transfers ({completion_to_transfer_ratio:.3f}).", "metrics": {"completion_to_transfer_ratio": completion_to_transfer_ratio}})
    if top_link_share >= 0.35 and canonical_total_bytes > 0:
        score = min(top_link_share * 2.0, 1.0)
        issues.append({"type": "link_hotspot", "severity": _severity(score), "score": score, "description": f"A single sender/receiver pair carries a large share of bytes ({top_link_share:.1%}).", "metrics": {"top_link_share": top_link_share}})
    issues.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    window_count = 1 if runtime <= 0.0 else min(40, max(10, total_events // 50000 + 10))
    time_windows = _build_time_windows(timeline_obj.generate_events(), total_events, window_count, runtime, start_t)

    print("\nAnalysis Complete.")
    return {
        "summary": {
            "total_events": total_events, "canonical_transfer_events": canonical_total_events,
            "canonical_transfer_bytes": canonical_total_bytes, "completion_events": completion_total_events,
            "barrier_events": barrier_total_events, "collective_events": collective_total_events,
            "estimated_runtime": runtime, "pair_density": pair_density, "avg_out_peers": avg_out_peers,
            "avg_in_peers": avg_in_peers,
        },
        "per_rank": per_rank_list, "top_ranks_by_out_bytes": top_ranks_by_out, "top_ranks_by_in_bytes": top_ranks_by_in,
        "top_ranks_by_touch_bytes": top_ranks_by_touch, "top_links": top_links, "collective_roots": rooted_collective_summary,
        "barrier_spreads": barrier_spreads, "patterns": patterns, "issues": issues, "time_windows": time_windows,
    }

# -----------------------------------------------------------------------------
# Main parser
# -----------------------------------------------------------------------------

def parse_mpic_file(mpic_filepath, hw_filepath=None):
    if not os.path.exists(mpic_filepath):
        print(f"Error: File '{mpic_filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    data = {
        "metadata": {"total_ranks": 0, "date": "", "program": "unknown", "system_name": "Unknown Cluster"},
        "topology": [], "time_anchors": [], "statistics": {}, "hardware_blueprint": None,
        "timeline": ColumnarTimeline()
    }

    hw_lookup = load_hardware_map(hw_filepath) if hw_filepath else {}

    with _open_maybe_gzip(mpic_filepath) as f:
        raw_file = f.read()

    try:
        metadata, topology, anchors, sections_offset = _parse_mpic_header(raw_file, hw_lookup)
    except Exception as exc:
        print(f"Error: failed to parse header: {exc}", file=sys.stderr)
        sys.exit(1)

    data["metadata"].update(metadata)
    data["topology"] = topology
    data["time_anchors"] = anchors

    raw_sections = raw_file[sections_offset:]

    try:
        _parse_sections_strict(raw_sections, data["metadata"]["total_ranks"], data)
    except Exception as strict_err:
        print(f"Warning: strict parse failed ({strict_err}). Falling back to salvage parser.", file=sys.stderr)
        data["timeline"] = ColumnarTimeline()
        data["statistics"] = {}
        try:
            _parse_sections_salvage(raw_sections, len(raw_sections), data)
        except Exception as salvage_err:
            print(f"Error: salvage parser failed: {salvage_err}", file=sys.stderr)
            sys.exit(1)

    # Remove the initial data that we've loaded in before analysis to save on memory
    del raw_file
    del raw_sections
    gc.collect()

    # Convert lists to  memory arrays to reduce memory footprint
    print("Finalizing Columnar NumPy Arrays...")
    data["timeline"].finalize_to_numpy()

    _apply_time_registration(data)

    print("Sorting the timeline vector-wise...")
    data["timeline"].sort_timeline()

    print("Reading in the hardware blueprint...")
    if hw_filepath and os.path.exists(hw_filepath):
        with open(hw_filepath, "r") as f:
            blueprint = json.load(f)
            data["hardware_blueprint"] = blueprint
            if "metadata" in blueprint and "system_name" in blueprint["metadata"]:
                data["metadata"]["system_name"] = blueprint["metadata"]["system_name"]

    data["analysis"] = analyse_trace(data)

    CHUNK_SIZE = 250000
    chunks_index = []
    current_byte_offset = 0

    total_events = len(data["timeline"])
    total_chunks = (total_events + CHUNK_SIZE - 1) // CHUNK_SIZE if total_events > 0 else 0

    output_filename = mpic_filepath
    if output_filename.endswith(".mpic.gz"): output_filename = output_filename[:-8] + ".mpix"
    elif output_filename.endswith(".mpic"): output_filename = output_filename[:-5] + ".mpix"
    else: output_filename = output_filename + ".mpix"

    temp_payload_file = output_filename + ".tmp"

    print(f"Compressing {total_chunks} chunks to temporary disk stream...")
    print_progress(0, max(total_chunks, 1), prefix='Compressing:  ', suffix='Complete', length=40)

    # Stream JSON chunks to disk to reduce memory usage
    with open(temp_payload_file, "wb") as f_tmp:
        events_gen = data["timeline"].generate_events()
        for idx in range(total_chunks):
            chunk_data = []
            for _ in range(min(CHUNK_SIZE, total_events - (idx * CHUNK_SIZE))):
                chunk_data.append(next(events_gen))
                
            chunk_json = json.dumps(chunk_data, separators=(",", ":")).encode("utf-8")
            compressed_chunk = zlib.compress(chunk_json)

            chunks_index.append({
                "t_start": chunk_data[0]["time"],
                "t_end": chunk_data[-1]["time"],
                "offset": current_byte_offset,
                "size": len(compressed_chunk),
            })

            f_tmp.write(compressed_chunk)
            current_byte_offset += len(compressed_chunk)
            
            # Help GC clean up the strings
            del chunk_data
            del chunk_json
            del compressed_chunk
            
            print_progress(idx + 1, max(total_chunks, 1), prefix='Compressing:  ', suffix='Complete', length=40)

    header_data = {
        "metadata": data["metadata"], "topology": data["topology"], "time_anchors": data["time_anchors"],
        "statistics": data["statistics"], "hardware_blueprint": data["hardware_blueprint"],
        "analysis": data["analysis"], "chunks": chunks_index,
    }

    header_json = json.dumps(header_data, separators=(",", ":")).encode("utf-8")
    compressed_header = zlib.compress(header_json)

    print("Stitching File container together...")
    with open(output_filename, "wb") as f_out, open(temp_payload_file, "rb") as f_tmp:
        f_out.write(struct.pack("<I", len(compressed_header)))
        f_out.write(compressed_header)
        while True:
            buf = f_tmp.read(8 * 1024 * 1024)  # 8MB Stream copy
            if not buf: break
            f_out.write(buf)

    os.remove(temp_payload_file)

    print(f"Packed {len(chunks_index)} chunks into a single {output_filename} container.")
    print(f"Parsed {len(data['timeline'])} communication events.")
    print(f"Data saved to {output_filename}")

    total_ranks = data["metadata"].get("total_ranks", 0)
    print_summary_table(data["statistics"], total_ranks)
    print_analysis_summary(data["analysis"], total_ranks)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_mpic.py <filename.mpic|filename.mpic.gz> [hardware_map.json]")
        sys.exit(1)

    hw_file = sys.argv[2] if len(sys.argv) > 2 else None
    parse_mpic_file(sys.argv[1], hw_file)
