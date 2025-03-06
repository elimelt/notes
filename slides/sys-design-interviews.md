<!-- 
Overview of system design interviews
 -->

<!-- backgroundColor: #121212 -->
<!-- color: #fff -->
<!-- style: normal -->

# System Design Interviews

---

## Agenda

- Introduce the concept of a system design interview
- Cover the format and structure of the interview, and what might be expected of you
- Some basic principles to get your started, and ways to learn more

---

## What is a System Design Interview?

- Given a set of features/requirements, you design the high level architecture and interface of a system
- Extremely open ended compared to coding interviews
- Tests your ability to gather/clarify requirements, evaluate tradeoffs, justify technical decisions, etc.
- Less common but still possible for intern/new grad
- Will come up more and more after you graduate, and is a useful skill to start developing

---

## Example:

Design a URL shortening service, which takes a long, complex web address and converts it into a shorter, more manageable link. This shorter URL redirects users to the original destination, making sharing links easier and cleaner

---

## Format/Structure of the Interview

- Requirements clarification (functional and non-functional)
- Back-of-envelope estimations (scale, throughput, storage)
- System interface design (APIs, data models)
- High-level architecture (components and data flow)
- Details of notable components
- Addressing bottlenecks and edge cases
- Trade-off discussion and potential improvements

Note: there is not one right way of doing them, and you might not need to touch on all of these.

---

## Format/Structure of the Interview

### Requirements clarification(functional and non-functional)

- functional: what your system does/features supported
- e.g. takes a long, complex web address and converts it into a shorter, more manageable link
- non-functional: everything else
- e.g. Support 3 million concurrent users at peak

---

## Format/Structure of the Interview

### Back-of-envelope estimations (scale, throughput, storage)

Calculate the expected scale of your system
- e.g. 100M new URLs per month = ~40 URLs/second
Estimate storage requirements-
- e.g. 500 bytes per URL × 100M = 50- GB/month
Determine read/write ratio-
- e.g. 10:1 read:write ratio = ~400 - reads/second
Calculate bandwidth needs
- e.g. 500 bytes × 400 reads/second = 200KB/second

---

## Format/Structure of the Interview

### System interface design (APIs, data models)

Define the API endpoints/interfaces
- e.g. createShortURL(api_key, original_url, custom_alias=null)
- e.g. getOriginalURL(short_url)
Specify input/output parameters
- e.g. Returns: shortened_url or error message
Define data models and schemas
- e.g. URL object: {id, original_url, short_key, created_at, expires_at}

---

## Format/Structure of the Interview

### High-level architecture (components and data flow)

Identify the main components of your system
- e.g. Load balancers, web servers, application servers, databases, caches
Show how data flows between components
- e.g. Client → Load balancer → Web server → App server → Database
Specify communication patterns
- e.g. Synchronous API calls, asynchronous message queues
Select technologies for each component
- e.g. NGINX for load balancing, Redis for caching, PostgreSQL for database

---

## Format/Structure of the Interview

### Details of notable components

Deep dive into 1-2 most important components
- e.g. URL shortening algorithm: MD5 hash + Base62 encoding
Explain specific algorithms or data structures
- e.g. Bloom filter to check if URL already exists
Database schema with tables and relationships
- e.g. URLs table with indexes on short_key for O(1) lookups
Caching strategy and policies
- e.g. LRU cache for frequently accessed URLs with 80% hit rate

---

## Format/Structure of the Interview

### Addressing bottlenecks and edge cases

Identify potential bottlenecks
- e.g. Database becomes read bottleneck at scale
Propose solutions for each bottleneck
- e.g. Add read replicas, implement caching layer
Discuss single points of failure
- e.g. Load balancer failover strategy with leader-follower setup
Handle edge cases
- e.g. URL collision resolution, handling expired URLs

---

## Format/Structure of the Interview

### Trade-off discussion and potential improvements

Discuss trade-offs made in your design
- e.g. Consistency vs availability: choosing eventual consistency
Cost vs performance considerations
- e.g. In-memory cache is faster but more expensive than disk storage
Security considerations
- e.g. Rate limiting to prevent abuse, input validation
Future improvements
- e.g. Geographic distribution for lower latency, analytics features

---

