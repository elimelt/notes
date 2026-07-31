#!/usr/bin/env python3
import argparse
import random
from collections import deque
from statistics import mean


def simulate(workers, tasks, seed):
    random.seed(seed)
    queues = [deque() for _ in range(workers)]
    for tid in range(tasks):
        queues[random.randrange(workers)].append(tid)

    local_runs = [0] * workers
    steals = [0] * workers

    while any(queues):
        for wid in range(workers):
            if queues[wid]:
                queues[wid].pop()
                local_runs[wid] += 1
                continue
            victims = [i for i in range(workers) if queues[i]]
            if not victims:
                continue
            victim = random.choice(victims)
            queues[victim].popleft()
            steals[wid] += 1

    return local_runs, steals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--tasks", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    local_runs, steals = simulate(args.workers, args.tasks, args.seed)
    print(f"workers={args.workers} tasks={args.tasks}")
    print(f"mean_local_runs={mean(local_runs):.2f}")
    print(f"mean_steals={mean(steals):.2f}")
    print(f"max_steals={max(steals)}")
    print(f"total_steals={sum(steals)}")


if __name__ == "__main__":
    main()

