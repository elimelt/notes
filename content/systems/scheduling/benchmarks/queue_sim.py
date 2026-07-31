#!/usr/bin/env python3
import argparse
import math
import random
from statistics import mean


def percentile(values, p):
    if not values:
        return 0.0
    idx = min(len(values) - 1, math.ceil(p * len(values)) - 1)
    return sorted(values)[idx]


def simulate(arrival_rate, service_rate, jobs, seed):
    random.seed(seed)
    now = 0.0
    server_free = 0.0
    responses = []
    waits = []

    for _ in range(jobs):
        interarrival = random.expovariate(arrival_rate)
        service = random.expovariate(service_rate)
        now += interarrival
        start = max(now, server_free)
        finish = start + service
        waits.append(start - now)
        responses.append(finish - now)
        server_free = finish

    return waits, responses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rho", type=float, default=0.8)
    parser.add_argument("--service-ms", type=float, default=1.0)
    parser.add_argument("--jobs", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    service_s = args.service_ms / 1000.0
    service_rate = 1.0 / service_s
    arrival_rate = args.rho * service_rate

    waits, responses = simulate(arrival_rate, service_rate, args.jobs, args.seed)
    theoretical = service_s / (1.0 - args.rho)

    print(f"rho={args.rho:.3f}")
    print(f"service_ms={args.service_ms:.3f}")
    print(f"jobs={args.jobs}")
    print(f"mean_wait_ms={mean(waits) * 1000:.3f}")
    print(f"mean_response_ms={mean(responses) * 1000:.3f}")
    print(f"p95_response_ms={percentile(responses, 0.95) * 1000:.3f}")
    print(f"p99_response_ms={percentile(responses, 0.99) * 1000:.3f}")
    print(f"mm1_mean_response_ms={theoretical * 1000:.3f}")


if __name__ == "__main__":
    main()

