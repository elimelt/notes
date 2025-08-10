---
title: Content Delivery Networks (CDNs)
category: Networks
tags: content delivery networks, web caching, proxy servers, edge locations, DNS resolution, cache control headers
description: Covers the implementation of content delivery networks (CDNs) and how they place content closer to clients. Discusses browser caching, proxy caches, and the use of edge locations and DNS resolution to efficiently deliver content. Examines the role of cache control headers in managing content caching and expiration.
---

# Content Delivery Networks (CDNs)

## How do you place content near clients?

### Browser Cache

Web browsers can cache static content such as stylesheets, scripts, images, and some AJAX requests. This caching can speed up page load time on subsequent page views.

When a web server returns a response, it sends a `Cache-Control` header. This header specifies the amount of time that a file should be cached. Once a file is cached in the browser, the browser will not request the file from the server until the file has expired.

## Proxy Caches

A proxy server is a server that sits between a client application, such as a web browser, and a real server. It intercepts all requests to the real server to see if it can fulfill the requests itself. If not, it forwards the request to the real server.

## Content Delivery Networks (CDNs)

A CDN is a system of distributed servers that deliver web content to a user based on the geographic locations of the user. Each region will have a number of edge locations, which are data centers that cache the content of the main server.

The DNS resolution of a CDN URL will direct the user to the nearest edge location, which will then deliver the cached content. This process reduces the load on the original server and speeds up the delivery of the content to the user.
