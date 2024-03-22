## Formalizing the Pairing Algorithm for the SWECC Mock Interview Program

Given $s$ signups, form pairs for all the students based on the following constraints:
- Each student should be paired with exactly one other student. If there are an odd number of students, one student will be left unpaired.
- A valid pair **must** have at least two 1-hour time slots in common in their availability. The number of common time slots is factored into the score of the pair.
- Each student responds to a form while signing up. The responses are vectorized, and pairings are made based on the similarity of the responses.

### Statement of the Problem

Let $T^{7 \times 24}_i$ be a bit-matrix of 1-hour time slots in a week for student $i$. The value of $T_{i,j,k}$ is 1 if student $i$ is available at time slot $(j,k)$, and 0 otherwise.

$$
T_i = \begin{bmatrix}
    t_{1,1} & t_{1,2} & t_{1,3}& \cdots & t_{1,24} \\
    t_{2,1} & t_{2,2} & t_{2,3}& \cdots & t_{2,24} \\
    \vdots & \vdots & \vdots & \ddots & \vdots \\
    t_{7,1} & t_{7,2} & t_{7,3}& \cdots & t_{7,24}
\end{bmatrix}
$$

Let $S$ be the set of students, and $A$ be the set of all possible pairings of students in $S$

$$
A = \{ (i, j) \mid (i, j) \in S \times S, i < j \}
$$

Now, enforcing a strict and repeatable ordering on the students through sorting, we have a mapping from $s_i \in S$ to $T_i$.

We use this ordering to define a scoring function $f: A \to \mathbb{R}$ that takes a pair of students and returns the number of common time slots in their availability, or $0$ if it is less than $2$. We then create a matrix $F_{time}$ of the scores of all possible pairings.

$$
F_{time} = \begin{bmatrix}
    f(s_1, s_2) & f(s_1, s_3) & \cdots & f(s_1, s_n) \\
    f(s_2, s_1) & f(s_2, s_3) & \cdots & f(s_2, s_n) \\
    \vdots & \vdots & \ddots & \vdots \\
    f(s_n, s_1) & f(s_n, s_2) & \cdots & f(s_n, s_{n-1})
\end{bmatrix}
$$

Next, we follow a similar pattern using the responses of the students. Let $R_i$ be the vectorized response of student $i$.

$$
R_i = \begin{bmatrix}
    r_{1} \\
    r_{2} \\
    \vdots \\
    r_{dim(R_i)}
\end{bmatrix}
$$

We define a scoring function $g: A \to \mathbb{R}$ as the euclidean distance between the responses of the students. We then create a matrix $F_{response}$ of the scores of all possible pairings.

$$
F_{response} = \begin{bmatrix}
    g(s_1, s_2) & g(s_1, s_3) & \cdots & g(s_1, s_n) \\
    g(s_2, s_1) & g(s_2, s_3) & \cdots & g(s_2, s_n) \\
    \vdots & \vdots & \ddots & \vdots \\
    g(s_n, s_1) & g(s_n, s_2) & \cdots & g(s_n, s_{n-1})
\end{bmatrix}
$$

Finally, we define a binary matrix $F_{valid}$ of the valid pairings. A valid pairing is one where the students have at least two common time slots in their availability, or rather when $F_{time, i, j} \neq 0$.

In python, this would look like:

```python
# student_i has availability matrix availabilities[i] and response vector responses[i]
availabilities = [ ... ] # list of availability matrices. Each matrix is a 7x24 bit-matrix
responses = [ ... ] # list of response vectors

def f(availability1, availability2):
    count = 0
    for i in availability1:
        for j in availability2:
            count += np.sum(i & j)

    return count if count >= 2 else 0

def g(response1, response2):
    return np.linalg.norm(response1 - response2)

F_time = np.zeros((len(students), len(students)))
F_response = np.zeros((len(students), len(students)))
F_valid = np.zeros((len(students), len(students)))

for i in range(len(students)):
    for j in range(len(students)):
        F_time[i, j] = f(availabilities[i], availabilities[j])
        F_response[i, j] = g(responses[i], responses[j])
        F_valid[i, j] = 1 if F_time[i, j] != 0 else 0
```

Finally, we normalize (min max) F_time and F_response and compute their sum's hadamard product with F_valid to get the final score matrix $F_{final}$.

$$
F_{final} = F_{valid} \odot \left( \frac{F_{time} - \min(F_{time})}{\max(F_{time}) - \min(F_{time})} + \frac{F_{response} - \min(F_{response})}{\max(F_{response}) - \min(F_{response})} \right)
$$

```python
def normalize(matrix):
    return (matrix - np.min(matrix)) / (np.max(matrix) - np.min(matrix))
F_final = F_valid * (normalize(F_time) + normalize(F_response))
```

Finally, using max-min fairness, we repeatedly find the student with the lowest max score for all their pairs, and select that maximal pair. We then update the scores of both students in the pair to be $0$ for all their pairs, and repeat the process until all students are paired.

```python
def next_pair(F_final):
  max_scores = [np.max(F_final[i]) for i in range(len(F_final))]
  s1, s2 = np.argmin(max_scores), np.argmax(F_final[student])
  for i in range(len(F_final)):
    F_final[s1, i] = 0
    F_final[i, s1] = 0
    F_final[s2, i] = 0
    F_final[i, s2] = 0
  return s1, s2

def calculate_pairs(F_final):
  pairs = []
  unpaired = set(range(len(students)))
  while len(pairs) < len(students) // 2:
    pairs.append(next_pair(F_final))
    unpaired.remove(pairs[-1][0])
    unpaired.remove(pairs[-1][1])
  return pairs
  ```


