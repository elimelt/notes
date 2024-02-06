# Byte Oriented Protocols, Point-to-point protocol (PPP)

## Byte-Oriented Framing

- Oldest approach, viewing frames as collections of bytes.
- Examples: BISYNC by IBM, DDCMP in DECNET, PPP.

## Length Field Approach

- Include frame byte count in header (DDCMP approach).
- Risk: Transmission error corrupting count field; framing error.

## Sentinel-based Approach/Byte Stuffing

- Use special characters (SYN, STX, ETX) to indicate frame boundaries.
- Challenge: Special characters in data; overcome by character stuffing or escape sequences similar to C.

## PPP Frame Format

- Used for IP packet transmission over point-to-point links.
- Start-of-text character (Flag field: 01111110).
- Negotiable field sizes, CRC used for checksum.

## LCP Protocol and Negotiation

- Link Control Protocol (LCP) negotiates field sizes in PPP.
- Controls encapsulated in PPP frames.
- Involvement in link establishment between peers.

# Bit Oriented Protocols (HDLC)

## Bit-Oriented Framing

- Views frames as a bit stream, not concerned with byte boundaries.
- Examples: SDLC developed by IBM, standardized as HDLC by ISO.

## HDLC Frame Format

- Denotes frame start and end with bit sequence 01111110.
- Uses sentinel approach, similar to byte-oriented protocols.
- Bit stuffing employed to handle the sequence within the frame.

### Bit Stuffing in HDLC

- Inserts 0 after five consecutive 1s during transmission.
- Receiver removes stuffed 0 based on the next bit.
- Distinguishes between end-of-frame marker and errors.

## Frame Size Dependency

- Frame size depends on payload data; not all frames can be the same size.
- Challenges with ensuring consistent frame size discussed in the next subsection.


# Clock-Based Protocols (SONET)

## Clock-Based Framing in SONET

- Exemplified by Synchronous Optical Network (SONET) standard.
- Addresses framing, encoding, and multiplexing for data over optical fiber.

## SONET Frame Structure

- SONET frame has special information for start and end.
- No bit stuffing used; frame length independent of data.
- Special bit pattern in STS-1 frame helps receiver locate frame boundaries.

## Overhead and Payload

- SONET complexity due to overhead bytes and network-level considerations.
- Payload bytes scrambled for clock recovery.
- SONET supports multiplexing of low-speed links.

## Multiplexing in SONET

- SONET links run at rates ranging from STS-1 to STS-768.
- A single SONET frame can contain subframes for multiple lower-rate channels.
- STS-N frame consists of N interleaved STS-1 frames.

## Concatenation in SONET

- STS-N signal used to multiplex N STS-1 frames; payload may be concatenated.
- Denoted as STS-Nc for concatenated links.
- Simplifies clock synchronization across carriers' networks.
