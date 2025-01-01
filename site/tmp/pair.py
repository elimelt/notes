import dataclasses
import numpy as np
from typing import List, Tuple
from model import SignupRecord


def f(availability1, availability2):
    return np.sum(availability1 & availability2)


def g(response1, response2):
    return np.linalg.norm(response1 - response2)


def normalize(matrix):
    mn, mx = matrix.min(), matrix.max()
    if mn == mx:
        return matrix
    return (matrix - mn) / (mx - mn)

def next_pair(F, unpaired):
    mrm, mrmi = np.inf, 0
    for i in unpaired:
        row_max = max(F[i, j] for j in unpaired if j != i)
        if row_max < mrm:
            mrm = row_max
            mrmi = i

    mrmj = 0
    for j in unpaired:
        if j != mrmi and F[mrmi, j] == mrm:
            mrmj = j
            break
    return mrmi, mrmj


def calc_pairs(F, unpairable=set()):

    unpaired = set(range(len(F)))
    unpaired -= unpairable
    pairs = []
    while len(unpaired) > 1:
        p1, p2 = next_pair(F, unpaired)
        unpaired.remove(p1)
        unpaired.remove(p2)
        pairs.append((p1, p2))

    return pairs, unpaired | unpairable


def pair_signups(signups: List[SignupRecord]) -> Tuple[List[Tuple[str, str]], List[str]]:
    availabilities = np.array([s.availability for s in signups])
    F_time = np.zeros((len(signups), len(signups)))
    F_valid = np.zeros((len(signups), len(signups)))

    for i in range(len(signups)):
        for j in range(len(signups)):
            F_time[i, j] = f(availabilities[i], availabilities[j])
            F_valid[i, j] = 1 if i != j and F_time[i, j] != 0 else 0

    unpairable = set()
    for i, Fvr in enumerate(F_valid):
        if max(Fvr) == 0:
            unpairable.add(i)

    scores = normalize(F_time * F_valid)

    pairs_indices, unpaired_indicies = calc_pairs(scores, unpairable)
    pairs = [(signups[p1].user_id, signups[p2].user_id) for p1, p2 in pairs_indices]
    unpaired = [signups[i].user_id for i in unpaired_indicies]
    return pairs, unpaired


import random
import uuid
import datetime


def generate_realistic_availability(sparse_probability: float = 0.3) -> List[List[int]]:
    availability = np.zeros((7, 24), dtype=int)

    # typical working hours (9 AM - 5 PM)
    runlen = int(random.random() * 5) + 1
    for day in range(5):  # Monday to Friday
        for hour in range(9, 17):  # 9 AM to 5 PM
            if runlen > 0:
                availability[day][hour] = 1
                runlen -= 1
            else:
                availability[day][hour] = 0
                runlen = int(random.random() * 5) + 1

    # randomly set availability for weekends
    for day in range(5, 7):  # Saturday and Sunday
        for hour in range(24):  # 24 hours
            if (
                random.random() < sparse_probability
            ):
                availability[day][hour] = 1

    return availability.tolist()  # Convert NumPy array to list


def generate_fake_data(num_entries: int) -> List[SignupRecord]:
    sparse_probabilities = [0.1, 0.3, 0.5, 0.7, 0.9]
    fake_data = []
    for _ in range(num_entries):
        created_at = datetime.datetime.utcnow().isoformat() + "+00:00"
        form_id = random.randint(1, 2)
        availability = generate_realistic_availability(
            random.choice(sparse_probabilities)
        )
        user_id = str(uuid.uuid4())

        fake_entry = SignupRecord(
            created_at=created_at,
            form_id=form_id,
            availability=availability,
            user_id=user_id,
        )

        fake_data.append(fake_entry)

    return fake_data


if __name__ == "__main__":
    students = generate_fake_data(500)
    pairs, unpaired = pair_signups(students)

    print("paired: ")
    for pair in pairs:
        print(pair)

    print("unpaired: ")
    for student in unpaired:
        print(student)

    if any(p[0] == p[1] for p in pairs):
        print("Error: a student is paired with themselves")

    seen = set()

    for p in pairs:
        if p[0] in seen or p[1] in seen:
            print("Error: a student is paired with multiple students")
        seen.add(p[0])
        seen.add(p[1])