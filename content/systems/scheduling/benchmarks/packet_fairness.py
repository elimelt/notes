#!/usr/bin/env python3
import argparse
from collections import deque


def make_flows():
    return {
        "a": deque([64] * 40),
        "b": deque([1500] * 10),
        "c": deque([512] * 20),
    }


def fifo(flows):
    merged = deque()
    for name, q in flows.items():
        for size in q:
            merged.append((name, size))
    sent = {"a": 0, "b": 0, "c": 0}
    while merged:
        name, size = merged.popleft()
        sent[name] += size
    return sent


def rr(flows, rounds):
    sent = {name: 0 for name in flows}
    order = list(flows)
    for _ in range(rounds):
        progressed = False
        for name in order:
            if flows[name]:
                sent[name] += flows[name].popleft()
                progressed = True
        if not progressed:
            break
    return sent


def drr(flows, quantum, rounds):
    sent = {name: 0 for name in flows}
    deficit = {name: 0 for name in flows}
    order = list(flows)
    for _ in range(rounds):
        progressed = False
        for name in order:
            deficit[name] += quantum
            while flows[name] and flows[name][0] <= deficit[name]:
                size = flows[name].popleft()
                sent[name] += size
                deficit[name] -= size
                progressed = True
        if not progressed and all(not q for q in flows.values()):
            break
    return sent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=200)
    parser.add_argument("--quantum", type=int, default=512)
    args = parser.parse_args()

    print("fifo", fifo(make_flows()))
    print("rr", rr(make_flows(), args.rounds))
    print("drr", drr(make_flows(), args.quantum, args.rounds))


if __name__ == "__main__":
    main()

