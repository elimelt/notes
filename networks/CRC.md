# CRC Algorithm

## sender

1. create binary representation of polynomial as divisor
2. append 0s to the end of the data to be sent, equal to the degree of the polynomial
3. divide the data by the polynomial, using XOR
4. change redundant bits to remainder

## reciever

1. create binary representation of polynomial as divisor
2. divide the data by the polynomial, using XOR
3. if the remainder is 0, then the data is valid

## Notes:

x + 1 as a generating polynomial is just a parity bit!