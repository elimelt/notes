"""Cycle-level 2D mesh NoC simulator, dimension-order (XY) routing.

Single-flit packets, per-link input buffers with credit-based backpressure,
round-robin output arbitration per router (same policy TLArbiter.roundRobin
uses in rocket-chip). Uniform-random traffic: every node injects toward a
uniformly random destination with Bernoulli probability `p` per cycle.

Run: python3 noc-latency-model.py
Deterministic given a fixed seed; three seeds are averaged per injection
rate to report run-to-run variability.
"""
import random
from collections import deque

ROWS, COLS = 4, 4
N = ROWS * COLS
DIRS = ["N", "S", "E", "W"]
BUFFER_DEPTH = 4
WARMUP_CYCLES = 500
MEASURE_CYCLES = 3000


def coords(node):
    return divmod(node, COLS)


def node_id(r, c):
    return r * COLS + c


def neighbor(node, direction):
    r, c = coords(node)
    if direction == "N" and r > 0:
        return node_id(r - 1, c)
    if direction == "S" and r < ROWS - 1:
        return node_id(r + 1, c)
    if direction == "E" and c < COLS - 1:
        return node_id(r, c + 1)
    if direction == "W" and c > 0:
        return node_id(r, c - 1)
    return None


def xy_next_hop(cur, dst):
    """Dimension-order routing: fix X (column) first, then Y (row)."""
    if cur == dst:
        return "L"
    cr, cc = coords(cur)
    dr, dc = coords(dst)
    if cc < dc:
        return "E"
    if cc > dc:
        return "W"
    if cr < dr:
        return "S"
    return "N"


class Packet:
    __slots__ = ("dst", "birth")

    def __init__(self, dst, birth):
        self.dst = dst
        self.birth = birth


def simulate(injection_rate, seed):
    rng = random.Random(seed)
    # input_buf[node][port]: packets currently held at `node`, arrived via `port`
    # port in {"N","S","E","W","L"}; "L" = freshly injected, waiting to route out.
    input_buf = {n: {p: deque() for p in DIRS + ["L"]} for n in range(N)}
    rr_state = {n: 0 for n in range(N)}  # round-robin pointer per router
    latencies = []
    delivered_measured = 0

    total_cycles = WARMUP_CYCLES + MEASURE_CYCLES
    for cycle in range(total_cycles):
        # Injection: Bernoulli(p) per node, uniform random destination != self.
        for n in range(N):
            if rng.random() < injection_rate and len(input_buf[n]["L"]) < BUFFER_DEPTH:
                dst = rng.randrange(N - 1)
                if dst >= n:
                    dst += 1
                input_buf[n]["L"].append(Packet(dst, cycle))

        # Per-router output arbitration: each output direction (incl. local
        # eject) picks at most one winning input port this cycle, round-robin.
        moves = []  # (from_node, from_port, out_dir)
        for n in range(N):
            ports = DIRS + ["L"]
            for out_dir in DIRS + ["EJECT"]:
                candidates = [
                    p for p in ports
                    if input_buf[n][p] and _wants(input_buf[n][p][0], n, out_dir)
                ]
                if not candidates:
                    continue
                start = rr_state[n] % len(ports)
                ordered = ports[start:] + ports[:start]
                winner = next(p for p in ordered if p in candidates)
                target = neighbor(n, out_dir) if out_dir != "EJECT" else None
                if out_dir == "EJECT" or (
                    target is not None
                    and len(input_buf[target][_opposite(out_dir)]) < BUFFER_DEPTH
                ):
                    moves.append((n, winner, out_dir))
                    rr_state[n] = (ports.index(winner) + 1) % len(ports)

        for n, from_port, out_dir in moves:
            pkt = input_buf[n][from_port].popleft()
            if out_dir == "EJECT":
                if cycle >= WARMUP_CYCLES:
                    latencies.append(cycle - pkt.birth)
                    delivered_measured += 1
            else:
                target = neighbor(n, out_dir)
                input_buf[target][_opposite(out_dir)].append(pkt)

    avg_latency = sum(latencies) / len(latencies) if latencies else float("inf")
    throughput = delivered_measured / (MEASURE_CYCLES * N)  # packets/cycle/node
    return avg_latency, throughput


def _wants(pkt, at_node, out_dir):
    hop = xy_next_hop(at_node, pkt.dst)
    return (out_dir == "EJECT" and hop == "L") or out_dir == hop


def _opposite(direction):
    return {"N": "S", "S": "N", "E": "W", "W": "E"}[direction]


if __name__ == "__main__":
    print(f"{ROWS}x{COLS} mesh, XY routing, buffer depth {BUFFER_DEPTH}, "
          f"{MEASURE_CYCLES} measured cycles after {WARMUP_CYCLES} warmup\n")
    print(f"{'p (inj/node/cyc)':>18} | {'avg latency (cyc)':>18} | {'throughput (pkt/node/cyc)':>26}")
    for p in [0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]:
        results = [simulate(p, seed) for seed in (1, 2, 3)]
        lat = [r[0] for r in results]
        thr = [r[1] for r in results]
        lat_mean = sum(lat) / len(lat)
        thr_mean = sum(thr) / len(thr)
        print(f"{p:>18.2f} | {lat_mean:>10.2f} (+/-{max(lat)-min(lat):.2f}) | "
              f"{thr_mean:>18.4f} (+/-{max(thr)-min(thr):.4f})")
