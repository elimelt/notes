#

Some bits will inevitably be recieved in error. We need to be able to...

- detect errors
- retransmit
- correct errors

## Problem: Noise

Noise may flip the bits recieved over the network. Once you 

## Approach: Add Redundancy

In error detection codes, add *check bits* to the message bits.

In error correction codes, add **more** *check bits* to let some errors be corrected.

Key issue is to design codes to detect as many errors as possible without having too much redundancy or computation required.


### Example Code:

$$
1 \to 11
0 \to 00
$$

For example:
$$
101110 \to 101110101110
$$

Can detect errors with this code up to 1 bit.

