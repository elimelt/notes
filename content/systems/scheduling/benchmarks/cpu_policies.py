#!/usr/bin/env python3
import argparse
import random
from collections import deque
from dataclasses import dataclass
from statistics import mean


@dataclass
class Job:
    jid: int
    arrival: int
    size: int


def generate_jobs(n, seed):
    random.seed(seed)
    jobs = []
    for jid in range(n):
        arrival = random.randint(0, n // 4)
        size = random.randint(1, 20)
        jobs.append(Job(jid, arrival, size))
    return jobs


def fifo(jobs):
    now = 0
    completion = {}
    for job in sorted(jobs, key=lambda j: (j.arrival, j.jid)):
        now = max(now, job.arrival)
        now += job.size
        completion[job.jid] = now
    return completion


def sjf(jobs):
    pending = sorted(jobs, key=lambda j: (j.arrival, j.jid))
    ready = []
    completion = {}
    now = 0
    i = 0
    while i < len(pending) or ready:
        while i < len(pending) and pending[i].arrival <= now:
            ready.append(pending[i])
            i += 1
        if not ready:
            now = pending[i].arrival
            continue
        ready.sort(key=lambda j: (j.size, j.arrival, j.jid))
        job = ready.pop(0)
        now += job.size
        completion[job.jid] = now
    return completion


def srpt(jobs):
    pending = sorted(jobs, key=lambda j: (j.arrival, j.jid))
    remaining = {job.jid: job.size for job in jobs}
    completion = {}
    now = 0
    i = 0
    ready = []
    while i < len(pending) or ready:
        while i < len(pending) and pending[i].arrival <= now:
            ready.append(pending[i])
            i += 1
        if not ready:
            now = pending[i].arrival
            continue
        ready.sort(key=lambda j: (remaining[j.jid], j.arrival, j.jid))
        job = ready[0]
        remaining[job.jid] -= 1
        now += 1
        if remaining[job.jid] == 0:
            completion[job.jid] = now
            ready.pop(0)
    return completion


def rr(jobs, quantum):
    pending = sorted(jobs, key=lambda j: (j.arrival, j.jid))
    remaining = {job.jid: job.size for job in jobs}
    completion = {}
    ready = deque()
    now = 0
    i = 0
    while i < len(pending) or ready:
        while i < len(pending) and pending[i].arrival <= now:
            ready.append(pending[i])
            i += 1
        if not ready:
            now = pending[i].arrival
            continue
        job = ready.popleft()
        run = min(quantum, remaining[job.jid])
        now += run
        remaining[job.jid] -= run
        while i < len(pending) and pending[i].arrival <= now:
            ready.append(pending[i])
            i += 1
        if remaining[job.jid] == 0:
            completion[job.jid] = now
        else:
            ready.append(job)
    return completion


def summarize(name, jobs, completion):
    responses = [completion[j.jid] - j.arrival for j in jobs]
    print(
        f"{name}: mean_response={mean(responses):.3f} "
        f"max_response={max(responses):.3f}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--quantum", type=int, default=2)
    args = parser.parse_args()

    jobs = generate_jobs(args.jobs, args.seed)
    summarize("fifo", jobs, fifo(jobs))
    summarize("sjf", jobs, sjf(jobs))
    summarize("srpt", jobs, srpt(jobs))
    summarize("rr", jobs, rr(jobs, args.quantum))


if __name__ == "__main__":
    main()

