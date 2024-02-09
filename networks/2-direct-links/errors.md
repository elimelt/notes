# Error Detection and Correction

Some bits will inevitably be recieved in error. Noise may flip the bits recieved over the network. We need to be able to...

- detect errors
- retransmit
- correct errors

## Approach: Add Redundancy

- In error detection codes, add *check bits* to the message bits.
- In error correction codes, add **more** *check bits* to let some errors be corrected.
- Key issue is to design codes to detect as many errors as possible without having too much redundancy or computation required.

Generally, a **codeword** is a $D$-bit message with $R$ check bits added to it. The sender computes the check bits and appends them to the message. The reciever then verifies the check bits by recomputing them and comparing them to the recieved check bits.


### Example Code:

$$
1 \to 11\\
0 \to 00\\
x \to xx\\
$$

For example:
$$
101110 \to 101110101110
$$

Can detect errors with this code up to 1 bit. However, no guarantee if more bits are flipped. Also cannot correct errors. This sucks.

## Intuition

Let $S$ be the set of all possible $n$-bit sequences, and let $C$ be the set of all $n$-bit code words with $D$ data bits and $R$ check bits. We have $C \subset S$, and we want to choose $C$ such that the probability of a random $D$-bit sequence being in $C$ is low.

Consider a random $n$-bit sequence $x \in S$...

$$
\mathbb{P}(x \in C) = \frac{|C|}{|S|} = \frac{2^R}{2^n} = 2^{-D}
$$

Error correction/detection is hard because even the check bits can be corrupted. Given $d$ errors, we can detect and correct $d$ errors if the distance between any two code words is $2d + 1$.

## Hamming Distance

Distance: The number of bit flips needed to change from one valid code word to another. The distance of a code is the minimum distance between any two code words. Letting $C$ be the set of all code words, the distance is:

$$
\min_{x, y \in C, x \neq y} d(x, y)
$$

- For a coding of distance $d + 1$, we can detect $d$ errors
- For a coding of distance $2d + 1$, we can correct $d$ errors by mapping to the closest code word.


## Internet Checksum

Sum up chunks of data and append the sum to the end of the data. If the sum is 0 on the recieving end, then the data is valid.

This code has a distance of 2, so it can detect 1 bit errors, and can correct 0 bit errors (since it can't correct any errors)

### Internet Checksum Algorithm

#### sender

1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.

#### reciever

1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.
4. If the sum is 0, then the data is valid.

```python
def internet_checksum(data):
    checksum = 0
    for i in range(0, len(data), 4):
        chunk = data[i:i+4]
        checksum += int.from_bytes(chunk, 'big')
    return checksum.to_bytes(4, 'big')
```

## Cyclical Redundancy Check (CRC)

Given a generator polynomial $C$ and a message of $n$ bits, generate $k$ bits such that the $n + k$ bit message is divisible by $C$. Works with binary values that operate over the field $\mathbb{Z}_2$ (mod 2 arithmetic).

### CRC Algorithm

#### sender

1. create binary representation of polynomial as divisor
2. append 0s to the end of the data to be sent, equal to the degree of the polynomial
3. divide the data by the polynomial, using XOR
4. change redundant bits to remainder

#### reciever

1. create binary representation of polynomial as divisor
2. divide the data by the polynomial, using XOR
3. if the remainder is 0, then the data is valid

### Notes:

x + 1 as a generating polynomial is just a parity bit!

## Hamming Code

A code with distance 3. Can detect 2 bit errors and correct 1 bit errors.

Uses $n = 2^k - k - 1$. Put check bits in positions that are powers of 2, and fill in the rest with data bits. Check bits are calculated by checking the bits in the ith position for all data bits whose ith bit is 1.

```python
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

### Algorithm

#### Send
1. Put all parity bits in positions that are powers of 2 (1, 2, 4, 8, 16, etc.)
2. Fill in all other positions with data bits.
3. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1)

#### Recieve
1. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1 of its index is a power of 2)
2. If the parity bits are all 0, then the data is valid (remove check bits from data bits)
3. If the parity bits are not all 0, then the data is invalid. The syndrome (concat and reverse the parity bits) is the index of the bit that is wrong. Flip that bit.


## Detection vs. Correction

- Error detection is easier than error correction. There is less overhead and computation required.
- Which is better depends on the pattern of errors. In general, error correction should be used when errors are detected and retransmission is expensive. Error detection should be used when errors are rare/unrecoverable, or when retransmission is cheap. Also used in application layer for physical storage (Reed-Solomon codes for CDs, DVDs, etc).

Error correction is heavily used in the physical layer. Low Density Parity Check (LDPC) codes are used in 802.11, DVB, WiMAX etc, and convolutional codes are used a lot in practice. On the other hand, detection combined with retranmission is used in the data link layer and above for residual errors.