## Hamming Distance & Hamming Code

Distance: The number of bit flips needed to change from one valid code word to another.

Given distance d, we can detect up to d

### Algorithm

#### Send
1. Put all parity bits in positions that are powers of 2 (1, 2, 4, 8, 16, etc.)
2. Fill in all other positions with data bits.
3. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1)

#### Recieve
1. calculate parity bits for each of the ith check bits. (check the bits in ith position for all data bits whose ith bit is 1 of its index is a power of 2)
2. If the parity bits are all 0, then the data is valid (remove check bits from data bits)
3. If the parity bits are not all 0, then the data is invalid. The syndrome (concat and reverse the parity bits) is the index of the bit that is wrong. Flip that bit.
