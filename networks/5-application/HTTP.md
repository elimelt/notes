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

