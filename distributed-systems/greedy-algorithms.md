 # Greedy Algorithms

 Choose the most attractive choice at each step, and hope that this will lead to the optimal solution. Proofs of correctness are particularly important for greedy algorithms.

 ## Interval Scheduling

 Job $j$ starts at $s(j)$ and finishes at $f(j)$. Two jobs are compatible if they don't overlap. The goal is to schedule as many jobs as possible without overlapping.

Start by sorting the jobs with $f(j)$, and iterate over the jobs in order and choose as many jobs as you can.

```python
def interval_scheduling(jobs):
  jobs.sort(key=lambda x: x[1])
  last = 0
  S = []
  for job in jobs:
    if job[0] >= last:
      S.append(job)
      last = job[1]
  return S
```

### Greedy Stays Ahead Proof

Suppose the above algorithm has chosen jobs $f(i_1) \le f(i_2) \le \ldots \le f(i_k)$, and suppose $f(j_1) \le f(j_2) \le \ldots \le f(j_m)$.

*Goal:* $m \le k$

*Lemma*: $\forall r$, $f(i_r) \le f(j_r)$

*Proof*: Induction, $P(r) := f(i_r) \le f(j_r)$

*Base Case*: $P(1)$. $i_1$ has the smallest finishing time.

*IH*: Assume $P(r - 1)$

*IS*: Goal $P(r)$

Applying $P(r - 1)$, and using the fact that both sets of jobs chosen are non-overlapping within themselves, we have...

$$
f(i_{r - 1}) \le f(j_{r - 1}) \le s(j_r)
$$

So $j_r$ is a candidate for $i_r$. However, greedy chose $i_r$, which implies $f(i_r) \le $f(j_r)$.
