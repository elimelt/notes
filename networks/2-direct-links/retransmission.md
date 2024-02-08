# Retransmission

Reliability is a key feature of a network, and there are measures in place accross the entire stack to ensure it.

## Automatic Repeat reQuest (ARQ)

Often used when errors are common or must be corrected (e.g. wireless links). Receiver automatically acknowledges correct frames, and sender retransmits frames that are not acknowledged by a certain timeout.

- **Stop and Wait ARQ**: Sender sends one frame, waits for an ACK, and then sends the next frame.
- **Sliding Window ARQ**: Sender can send multiple frames before waiting for an ACK. For a window size of $n$, the sender can send $n$ frames per RTT.
- **Go-Back-N ARQ**: Sender can send multiple frames before waiting for an ACK, but if a frame is lost, the sender must retransmit all frames from the lost frame onwards.

### Timeouts

They need to be not too long (link is idle), but also not too short (link is busy). Timeouts are easy to set in a LAN, but harder over the internet where latency can vary greatly.

### Sequence Numbers

Both frames and ACKs are numbered, so that the sender knows which frames are acknowledged. In **stop and wait ARQ**, the sequence number is 0 or 1. In **go-back-N ARQ** and **sliding-window ARQ**, the sequence number is a number modulo $2^k$.


### Limitations of Stop and Wait ARQ

- Allows for only a single frame to be outstanding at a time.
- Good for LAN, but bad for networks with high BD product (*bandwidth-delay product*).


### Examples

(These are just pseudocode examples)

```python
# Stop and Wait ARQ
def sender():
    while True:
        frame = create_frame()
        send_frame(frame)

        ack_received = wait_for_ack()

        if ack_received:
            break

def receiver():
    while True:
        frame = receive_frame()
        process_frame(frame)

        send_ack()

```

```python
# Sliding Window ARQ
def sender():
    window_size = 3
    frames = [create_frame() for _ in range(window_size)]
    send_frames(frames)

    acknowledged_frames = wait_for_acknowledgment()

    # Move window forward
    frames = frames[len(acknowledged_frames):] + [create_frame()]
    send_frames(frames)

def receiver():
    while True:
        frames = receive_frames()
        process_frames(frames)

        send_acknowledgment()
```

```python
# Go-Back-N ARQ
def sender():
    window_size = 3
    frames = [create_frame() for _ in range(window_size)]
    send_frames(frames)

    while True:
        acknowledged_frames = wait_for_acknowledgment()

        if not acknowledged_frames:
            resend_frames(frames)

def receiver():
    expected_frame = 0

    while True:
        frames = receive_frames()

        for frame in frames:
            if frame.sequence_number == expected_frame:
                process_frame(frame)
                expected_frame += 1

        send_acknowledgment()
```