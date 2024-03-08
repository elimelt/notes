# Hyper Text Transfer Protocol (HTTP)

You can think of a web page as a set of related HTTP transactions. Each transaction consists of a request and a response, which runs on TCP (typically on port 80).

## Fetching a Web Page

```plaintext
protocol://host:port/path
```

1. Resolve server to IP address using **DNS**.
2. Establish a **TCP** connection to the server.
3. Send an **HTTP** request for the page.
4. Await HTTP response
5. Execute/fetch embedded resources and render the page.
6. Close the TCP connection.

### Static vs. Dynamic Web-pages

Static web pages are pre-built and served as-is to the client. Dynamic web pages are built on the server and served to the client to be run/interpreted (usually with JavaScript).

### Methods

| Method | Description |
| --- | --- |
| GET | Read a Web page |
| HEAD | Read a Web page's header |
| POST | Append to a Web page |
| PUT | Store a Web page |
| DELETE | Remove the Web page |
| TRACE | Echo the incoming request |
| CONNECT | Connect through a proxy |
| OPTIONS | Query options for a page |

### Status Codes

| Code | Description | Example |
| --- | --- | --- |
| 1xx | Informational | 100 Continue - server agrees to handle client's request |
| 2xx | Success | 201 Created - resource created - posted data |
| 3xx | Redirection | 304 - Not Modified - client should use cached version |
| 4xx | Client Error | 404 Not Found - resource not found |
| 5xx | Server Error | 503 Service Unavailable  - server overloaded |

### Performance

#### Page Load Time (PLT)

The time it takes to download and display the entire content of a web page in the browser. Small increases in PLT can have a significant impact on user satisfaction. Depends on many factors including the page's content, the network RTT and bandwidth, and HTTP caching/TCP optimizations.

#### HTTP/1.0

Uses one TCP connection per request. This can be slow due to the overhead of setting up and tearing down connections. Also used sequential requests to all resources, requiring multiple TCP connections to the same server.

#### Decreasing PLT

- Reduce content size (minify, compress, etc.)
- Change protocol to make more efficient use of TCP (HTTP/2)
- Reduce the number of round trips (e.g., DNS prefetching, cahing, proxying)
- Move content closer to the client (CDN, edge caching)

In practice, this might look like:

- Browser runs multiple HTTP instances in parallel to fetch resources? Not good in practice, exacerbating network bursts and loss.
- Make a single TCP connection to the server and multiplex multiple HTTP requests over it. Issue of how long to keep the connection open, and can actually be slower for some use cases.

### HTTP Caching and Proxies

Users often revisit web pages, so caching is important. Some strategies include:

- **Expires** header: specifies a date after which the resource is invalid.
- **Heuristic expiration**: cacheable, freshly valid, not modified recently.
- **Revalidation**: check with the server if the resource is still valid.

Proxies can cache resources on behalf of clients, reducing the load on the server and speeding up the response time for clients. However, they can also introduce security and privacy concerns.

The general workflow for a proxy is:

1. Client sends a request to the proxy.
2. Proxy checks the expiry for the resource
3. If the resource is still valid, the proxy returns it to the client. Otherwise, the proxy fetches the resource from the server.
4. The proxy fetches the resource, and maybe some metadata through headers like Not-Modified and updates its cache.
5. The proxy returns the resource to the client.

This places an intermediary between the pool of clients and the server, which can be useful for load balancing, security, and privacy. Has the added benefit of being able to improve physical locality of data to be closer to clients while in the cache. Benefits are limited by secure/dynamic content, and the "long tail" of resources that are rarely accessed.



