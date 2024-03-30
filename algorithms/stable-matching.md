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

note: $p \to q$ is equiv to $p \land \neg q \equiv F$

#### Output is always perfect:

Suppose there is a company $c_1$ with no match after the algorithm terminates. Therefore, there is also an unmatched applicant.

$$
\exists \text{ unmatched company } \leftrightarrow \exists \text{ unmacted person}
$$

By observation, in order for a company to be unmatched, it will need to have proposed to and been rejected by every applicant. On the other hand, for an applicant to remain unmatched, it would need to have never been proposed to.

This means there is an applicant that was never proposed to by the unmatched company, which is a contradiction.

#### Output is a stable matching

For the sake of contradiction, suppose there exists an unstable pair not matched.

Let $S$ be the output of the GS algorithm, and $(c, a)$ to be some unstable pair. Since $S$ is perfect, there is an existing pair $(c, a') \in S$. Furthermore, since $S$ is unstable, we have that $c >_{a} c'$ and $a' >_{c} a$.

But $c$ must have proposed to and been rejected by $a$. Additionally, $a$ must have traded $c$ for a *better* company. Yet, $a$ ends up with a less preferred company, which is a contradiction.

## GS Solution Properties

### Company Optimal Assignments

- **Valid partner**: A company $c$ is a valid partner of applicant $a$ if there exists a stable matching in which they are matched.
- **Best valid partner**: The best valid partner of $c$ is the most preferred valid partner of $c$.

**Claim**: If you run GS, every company receives their BVP. Furthermore, the output of GS is unique.

#### Proof

Proof by contradiction. Suppose that some company c is not matched with their BVP. Since companies propose in decreasing order of preference, there must exist a company $c$ that was rejected by their best valid partner $BVP(c) = a$.

Consider the moment when $a$ rejects $c$. Let $S^*$ be the **current** state of the algorithm. Therefore, $a$ is matched to some other company $c'$. 

$$
a \in valid(c) \to \exists \text{ stable matching } S \text{ such that } (c, a) \in S
$$

Say $(c', a') \in S$. If $a >_{c'} a'$, then $(a, c')$ is unstable for $S$, which is a contradiction to the preceding claim. Therefore, we must have $a' >_{c'} a$. This also implies that $c'$ is also rejected by $BVP(c')$, since $c'$ proposed in decreasing order of preference, so it must already be rejected by $a'$.

We can continue the same line of reasoning since $c'$ is also rejected by $BVP(c')$, and so on. This is a contradiction because $c$ is the first company rejected by their BVP.

### Applicant Pessimality

**Claim**: Each applicant receives their **worst valid partner** (self descriptive).

#### Proof

Let $S^*$ be the output of $GS$. For cont. suppose $(c, a) \in S^*$, but $c \ne WVP(a)$.

Say $c' = WVP(a)$. Since $c' \in valid(a)$, $\exists \text{ stable matching } S$ such that $(c', a) \in S$. Further, suppose $(c, a') \in S$. 

If $a >_{c} a'$, then $(c, a)$ is unstable for $S$. Therefore, we must have $a' >_{c} a$. If $a' >_{c} a$, then by the above prove, $a = BVP(c)$. That is a contradiction because $a'$ is also valid.


### Efficient Implementation

Can be implemented in $O(n^2)$ time.

Companies are named $1, ..., n$, and students are named $n + 1, ..., 2n$. Each company has a list of preferences of students, and each student has a list of preferences of companies.

The key idea is to also maintain an inverse array of the preference index for a matching. 

```python
for i in range(n):
    for j in range(n):
        inverse[i][pref[i][j]] = j
```


# Stable Roommate Problem

Given a list of $2n$ people, each person ranks the other $2n - 1$ people in order of preference from $1$ to $2n - 1$. Find a stable matching between the people.


## Does a stable match always include at least one person's top choice?

No! Consider every possible instance of a stable matching problem with $n = 3$. By brute force, you can find plenty (12) unique examples where no person is matched with their top choice.

```python
from itertools import permutations, product

def is_stable_matching(company_prefs, applicant_prefs, matching):
    imatching = { v:k for k, v in matching.items() }
    for company, applicant in matching.items():
        company_index = company_prefs[company].index(applicant)
        for other_applicant in company_prefs[company][:company_index]:
            if applicant_prefs[other_applicant].index(company) < applicant_prefs[other_applicant].index(imatching[other_applicant]):
                return False
    return True

def find_stable_matchings(company_prefs, applicant_prefs):
    matchings = []
    for perm in permutations(applicant_prefs.keys()):
        matching = dict(zip(company_prefs.keys(), perm))
        if is_stable_matching(company_prefs, applicant_prefs, matching):
            matchings.append(matching)
    return matchings


A1, A2, A3 = 'A1', 'A2', 'A3'
C1, C2, C3 = 'C1', 'C2', 'C3'

def generate_preferences():

    company_labels = [C1, C2, C3]
    applicant_labels = [A1, A2, A3]

    cperms = list(permutations(company_labels))
    aperms = list(permutations(applicant_labels))

    cprod = product(cperms, cperms, cperms)
    aprod = product(aperms, aperms, aperms)

    c = [ dict(zip(applicant_labels, c)) for c in cprod ]
    a = [ dict(zip(company_labels, a)) for a in aprod ]

    return c, a

all_c, all_a = generate_preferences()

data = []
res = []
for c in all_c:
  for a in all_a:

    stable_matchings = find_stable_matchings(c, a)

    for matching in stable_matchings:
      imatching = { v: k for k, v in matching.items() }
      match_dict = dict(matching)
      match_dict.update(imatching)

      data.append((c, a, matching))
      curr = 0
      for co, pref in c.items():
        if pref[0] == match_dict[co]:
          curr += 1

      for ap, pref in a.items():
        if pref[0] == match_dict[ap]:
          curr += 1

      res.append(curr)


candidates = []

for i in range(len(res)):
  if res[i] == 0:
    candidates.append(data[i])
    print(data[i])
```
