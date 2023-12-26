# Chapter 3
## Encoding and Evolution

**evolvability**: the ability to evolve as requirements change.

**schema-on-read**: schema isn't enforced when data is written, only when it is read. it can change over time.

**schema-on-write**: schema is enforced when data is written. it is usually enforced by a database schema.

**backward compatibility**: new code can read data that was written by old code, meaning new code understands old fields.

**forward compatibility**: old code can read data that was written by new code, meaning old code ignores new fields.

### Formats for Encoding Data

Programs typically work with at least two different representations of data: 
- **in-memory data structures** (objects, arrays, hash maps, etc.)
- **serialized** (encoded) **bytes** (often stored on disk or sent over the network).

**serialization**: the process of translating data structures or object state into a format that can be stored (for example, in a file or memory buffer) or transmitted (for example, across a network connection link) and reconstructed later (possibly in a different computer environment).