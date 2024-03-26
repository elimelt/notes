# Stable Matching

Given a list of $n$ companies $c_1, c_2, \ldots, c_n$, and a list of students $s_1, s_2, \ldots, s_n$, each company ranks the students in order of preference, and each student ranks the companies in order of preference.

Find a **stable matching** between the companies and students, where no company and student would prefer each other over their current match.

- **perfect matching**: every company and student is matched with exactly one other company or student.
- **stable**: no pairs $(c, s)$ and $(c', s')$ such that $c$ prefers $s'$ over $s$ and $s'$ prefers $c$ over $c'$.

A stable matching is a perfect and stable matching. In other words, there should be no incentive for any company or student to break up their current match.

You can confirm a matching is stable by checking all non-existant matches and seeing if they are preferred. So with $n$ pairs, there are $n(n - 1)$ pairs to check to confirm stability.

Stable matches are guaranteed to exist.

## Propose and Reject Algorithm (Gale-Shapley)

```plaintext
Initialize all companies and students to be free

while some company is free and hanst proposed to all students:
    c = first such company
    s = some student c has not yet proposed to
    if s is free:
        (c, s) become paired
    else if s prefers c to current match c':
        c' becomes free
        (c, s) become paired
    else:
        s rejects c

return the set of pairs
```

```python
def GS(C, S):
    # C: list of companies
    # S: list of students
    n = len(C)
    free = set(C)
    matches = {c: None for c in C}
    while free:
        c = free.pop()
        for s in c.prefs:
            if matches[s] is None:
                matches[s] = c
                break
            elif s.prefs.index(c) < s.prefs.index(matches[s]):
                free.add(matches[s])
                matches[s] = c
                break
    return matches
```


### Properties

- Companies propose to students in descreasing order of preference
- Each company proposes to each student at most once
- Once an applicant is matched, never become unmatched, only "traded up"

### Proof of Correctness

When designing/analyzing algorithms, need to show the following:

- (1) The algorithm terminates with a reasonable running time
- (2) The algorithm is correct (produces a stable matching)

(1) Since $n$ companies propose to at most $n$ students, the algorithm runs in $O(n^2)$ time.

(2) Proof by contradiction

#### Output is always perfect:

Suppose there is a company $c_1$ with no match after the algorithm terminates.

# Stable Roommate Problem

Given a list of $2n$ people, each person ranks the other $2n - 1$ people in order of preference from $1$ to $2n - 1$. Find a stable matching between the people.