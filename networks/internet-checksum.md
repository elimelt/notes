# Algorithm

## sender

1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.


## reciever
 
1. Split up data into 4 byte chunks.
2. Sum up all the 4 byte chunks, wrapping around for carry beyond 4 bytes.
3. netgate append the checksum to the end of the data.
4. If the sum is 0, then the data is valid.
