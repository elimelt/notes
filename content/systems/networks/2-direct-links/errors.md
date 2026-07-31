---
title: Error Detection and Correction
aliases:
  - networks/2-direct-links/errors
category: Networks
tags:
  - error-detection
  - error-correction
  - redundancy
  - codewords
  - hamming-distance
  - checksum
  - crc
date: 2024-01-26
updated: 2026-07-30
status: needs-review
description: Error detection and correction by adding redundancy. Covers codewords and Hamming distance, the Internet checksum, CRC, and Hamming codes, and when to detect versus correct. Code snippets are unverified sketches.
sources:
  - title: "RFC 1071: Computing the Internet Checksum"
    url: https://www.rfc-editor.org/rfc/rfc1071
    type: rfc
  - title: "Computer Networks: A Systems Approach (Peterson and Davie)"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Some received bits will be wrong. Noise flips bits in flight, so a link needs a way to detect errors, and then either retransmit (see [[systems/networks/2-direct-links/retransmission|retransmission]]) or correct them in place. This note covers the codes that make both possible.

## Approach: add redundancy

Error detection codes add *check bits* to the message bits. Error correction codes add more check bits, enough to let some errors be fixed without retransmission. The design problem is catching as many errors as possible without paying too much in redundancy or computation.

A **codeword** is a $D$-bit message with $R$ check bits appended. The sender computes the check bits and appends them. The receiver recomputes them from the data and compares against what arrived.

### Example code

Repeat every bit:

$$
1 \to 11\\
0 \to 00\\
x \to xx\\
$$

For example:

$$
101110 \to 101110101110
$$

This detects any single bit flip, since a flip breaks one of the pairs. It gives no guarantee for two or more flips, and it can't correct anything, all while doubling the message size. Weak protection at a high price.

## Intuition

Let $S$ be the set of all $n$-bit sequences and $C \subset S$ the set of valid codewords, where $n = D + R$. There are $2^D$ codewords, one per data pattern. We want a random corruption to land on a valid codeword as rarely as possible. For a random $x \in S$:

$$
\mathbb{P}(x \in C) = \frac{|C|}{|S|} = \frac{2^D}{2^{D+R}} = 2^{-R}
$$

So every check bit halves the chance that random garbage looks valid. The check bits themselves can be corrupted too, which is what makes the design problem interesting.

## Hamming distance

The distance between two codewords is the number of bit flips needed to turn one into the other. The distance of a code is the minimum over all pairs:

$$
\min_{x, y \in C, x \neq y} d(x, y)
$$

- A code of distance $d + 1$ can detect $d$ errors, since $d$ flips can't reach another valid codeword.
- A code of distance $2d + 1$ can correct $d$ errors by mapping the received word to the closest codeword. With fewer than $d+1$ flips, the original codeword is still the unique nearest one.

## Internet checksum

Sum the data in fixed-size chunks and append the sum. The receiver sums the data plus the checksum and checks for the expected result.

The real Internet checksum ([RFC 1071](https://www.rfc-editor.org/rfc/rfc1071)) sums 16-bit words in ones' complement arithmetic, folding carries back in, and transmits the complement of the sum. The version below is the simplified form from lecture.

This code has distance 2, so it detects single-bit errors and corrects nothing.

### Internet checksum algorithm

Sender:

1. Split the data into chunks.
2. Sum the chunks, wrapping carries back into the sum.
3. Append the (complemented) sum to the data.

Receiver:

1. Split the received data, including the checksum, into chunks.
2. Sum the chunks the same way.
3. If the result is the expected check value, the data passes.

```python
# Simplified sketch, not RFC 1071. Real code uses 16-bit words,
# ones' complement addition, and transmits the complement.
def internet_checksum(data):
    checksum = 0
    for i in range(0, len(data), 4):
        chunk = data[i:i+4]
        checksum += int.from_bytes(chunk, 'big')
    return checksum.to_bytes(4, 'big')
```

## Cyclic redundancy check (CRC)

Given a generator polynomial $C$ of degree $k$ and an $n$-bit message, generate $k$ check bits such that the $n + k$ bit message is divisible by $C$. The arithmetic is over $\mathbb{Z}_2$, so addition and subtraction are both XOR.

### CRC algorithm

Sender:

1. Write the generator polynomial as a binary divisor.
2. Append $k$ zeros to the data, where $k$ is the degree of the polynomial.
3. Divide the padded data by the polynomial using XOR.
4. Replace the appended zeros with the remainder.

Receiver:

1. Divide the received bits by the same polynomial using XOR.
2. If the remainder is 0, the data passes.

Using $x + 1$ as the generator polynomial gives exactly a parity bit.

## Hamming code

A code with distance 3. It detects 2-bit errors and corrects 1-bit errors.

For $k$ check bits, the code carries $n = 2^k - k - 1$ data bits. Check bits sit at the positions that are powers of 2, and data bits fill the rest. Check bit $i$ covers every position whose binary index has bit $i$ set, so each position is covered by a unique combination of check bits.

Send:

1. Put check bits at the power-of-2 positions (1, 2, 4, 8, ...).
2. Fill the remaining positions with data bits.
3. Compute each check bit as the parity of the positions it covers.

Receive:

1. Recompute each check bit over the positions it covers.
2. If all parities are 0, the data is valid. Strip the check bits.
3. Otherwise, the parities concatenated (the syndrome) spell out the index of the flipped bit. Flip it back.

```python
# Unverified sketch of the encoder.
def hamming_encode(data):
    n = len(data)
    k, acc = 0, 1
    while acc < n + k + 1:
        k += 1
        acc *= 2

    code = [0] * (n + k)
    j = 0
    for i in range(1, n + k + 1):
        if i & (i - 1) == 0:
            code[i - 1] = 0
        else:
            code[i - 1] = data[j]
            j += 1
    for i in range(k):
        j = 2 ** i
        for l in range(j, n + k + 1):
            if l & j:
                code[j - 1] ^= code[l - 1]
    return code
```

## Detection vs. correction

Detection is cheaper than correction in both overhead and computation. Which one to use depends on the error pattern and the cost of retransmission. Correction wins when errors are common or retransmission is expensive. Detection wins when errors are rare and retransmission is cheap.

In practice, error correction dominates the physical layer, where LDPC codes appear in 802.11, DVB, and WiMAX, and convolutional codes are widely used. Detection paired with retransmission handles residual errors at the data link layer and above. Storage systems use correction too, such as Reed-Solomon codes on CDs and DVDs.

## Related notes

- [[systems/networks/2-direct-links/retransmission|retransmission]]
- [[systems/networks/1-physical/coding-and-modulation|coding and modulation]]
- [[systems/networks/2-direct-links/framing|framing]]
