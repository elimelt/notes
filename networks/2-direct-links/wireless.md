# Wireless

Wireless media is infinite, and therefore cannot carrier sense. Futhermore, nodes cannot hear the network while sending

## Hidden Terminal Problem

Two nodes are out of range of each other, but in range of a third node. The third node can hear both nodes, but the two nodes cannot hear each other. This can cause collisions at the node in the middle.

## Exposed Terminal Problem

Two nodes are in range of each other, but are sending to different nodes out of each other's range. The two nodes can hear each other, but are not in each other's way. The two nodes should be able to send at the same time, but this might be prevented by some protocols.

## Multiple Access with Collision Avoidance (MACA)

Uses short handshake instead of CSMA. Collisions are still possible, but less likely.

1. **Request to Send (RTS)**: Sender sends a request to send to the receiver.
2. **Clear to Send (CTS)**: Receiver sends a clear to send to the sender, including the frame size.
3. **Data**: Sender sends the frame while nodes that heard the CTS stay silent.


## 802.11 (WiFi)

Clients connect to the network through an **access point (AP)**.

## Physical Layer
- Uses 20/40 MHz channels on ISM (unlicensed) bands
  - 802.11b/g/n on 2.4 GHz
  - 802.11 a/n on 5 GHz
- OFDM modulation (except legacy 802.11b)
  - Different amplitudes/phases for varying SNRs
  - Rates from 6 to 54 Mbps plus error correction
  - 802.11n uses multiple antennas

## Link Layer
- Multiple access uses CSMA/CA; RTS/CTS optional
- Frames are ACKed and retransmitted with ARQ
- Three addresses due to AP
- Errors are detected with a 32-bit CRC
- Features like encryption, power save

## Centralized MAC: Cellular

Usually on a very limited spectrum because there are more regulations on non-ISM bands. The base station coordinates the transmissions of the mobiles, and is able to provide more strict control over the network to provide things like QoS and robustness.

GSM MAC uses FDMA/TDMA, and BEB for random access. One channel for coordination, and other channels for traffic. There is also a dedicated channel for QoS.