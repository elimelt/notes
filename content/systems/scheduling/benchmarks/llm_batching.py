#!/usr/bin/env python3
import argparse
import random
from collections import deque
from dataclasses import dataclass
from statistics import mean


@dataclass
class Request:
    rid: int
    arrival: int
    prompt: int
    decode: int
    remaining_prefill: int
    remaining_decode: int
    first_token_time: int | None = None
    done_time: int | None = None


def make_requests(n, seed):
    random.seed(seed)
    reqs = []
    for rid in range(n):
        prompt = random.randint(128, 4096)
        decode = random.randint(32, 1024)
        arrival = random.randint(0, n // 4)
        reqs.append(
            Request(
                rid=rid,
                arrival=arrival,
                prompt=prompt,
                decode=decode,
                remaining_prefill=prompt,
                remaining_decode=decode,
            )
        )
    return sorted(reqs, key=lambda r: (r.arrival, r.rid))


def simulate(requests, kv_budget_tokens, batch_token_budget, chunk):
    time = 0
    pending = deque(requests)
    waiting = deque()
    active = []
    completed = []

    while pending or waiting or active:
        while pending and pending[0].arrival <= time:
            waiting.append(pending.popleft())

        live_tokens = sum(r.prompt + (r.decode - r.remaining_decode) for r in active)
        batch_budget = batch_token_budget

        for r in list(active):
            if r.remaining_decode > 0:
                r.remaining_decode -= 1
                batch_budget -= 1
                if r.first_token_time is None:
                    r.first_token_time = time + 1
                if r.remaining_decode == 0:
                    r.done_time = time + 1

        active = [r for r in active if r.done_time is None]

        while waiting and batch_budget > 0:
            r = waiting[0]
            predicted_live = r.prompt + r.decode
            if live_tokens + predicted_live > kv_budget_tokens:
                break
            if r.remaining_prefill > 0:
                take = min(chunk, r.remaining_prefill, batch_budget)
                r.remaining_prefill -= take
                batch_budget -= take
                if r not in active:
                    active.append(r)
                    live_tokens += predicted_live
                if r.remaining_prefill == 0:
                    waiting.popleft()
                else:
                    break
            else:
                waiting.popleft()

        for r in list(active):
            if r.done_time is not None:
                completed.append(r)

        time += 1

    ttft = [r.first_token_time - r.arrival for r in requests if r.first_token_time is not None]
    e2e = [r.done_time - r.arrival for r in requests if r.done_time is not None]
    return ttft, e2e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=256)
    parser.add_argument("--kv-budget-tokens", type=int, default=262144)
    parser.add_argument("--batch-token-budget", type=int, default=8192)
    parser.add_argument("--chunk", type=int, default=512)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    requests = make_requests(args.requests, args.seed)
    ttft, e2e = simulate(
        requests,
        kv_budget_tokens=args.kv_budget_tokens,
        batch_token_budget=args.batch_token_budget,
        chunk=args.chunk,
    )
    print(f"requests={args.requests}")
    print(f"mean_ttft_steps={mean(ttft):.2f}")
    print(f"p95_ttft_steps={sorted(ttft)[int(0.95 * len(ttft))]:.2f}")
    print(f"mean_e2e_steps={mean(e2e):.2f}")
    print(f"max_e2e_steps={max(e2e):.2f}")


if __name__ == "__main__":
    main()

