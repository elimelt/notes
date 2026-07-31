---
title: Content Delivery Networks (CDNs)
category: Networks
tags:
  - content-delivery-networks
  - web-caching
  - proxy-servers
  - edge-locations
  - DNS
date: 2024-03-07
updated: 2026-07-30
status: evergreen
description: The three layers of moving web content closer to clients, browser caches, proxy caches, and CDN edge locations reached through DNS resolution.
sources:
  - title: "CSE 461: Computer Networks, University of Washington"
    url: https://courses.cs.washington.edu/courses/cse461/
    type: lecture
  - title: "Computer Networks: A Systems Approach"
    url: https://book.systemsapproach.org/
    type: textbook
---

## Purpose

Answer one question, how do you place content near clients, and walk through the three mechanisms that do it at increasing distance from the user.

## Browser cache

The cache closest to the user lives in the browser itself. Browsers cache static content like stylesheets, scripts, images, and some AJAX responses, which speeds up repeat visits.

The server controls this with the `Cache-Control` header on its responses, which states how long the file may be cached. Until that time expires, the browser serves the file locally without contacting the server at all.

## Proxy caches

A proxy server sits between a client application and the real server. It intercepts requests and checks whether it can fulfill them from its own cache, forwarding to the real server only on a miss. One proxy serves a pool of clients, so a file fetched for one user can be served from the proxy to everyone behind it. The caching mechanics and their limits are covered in [[networks/5-application/HTTP|HTTP]].

## CDNs

A CDN pushes the same idea out to global scale. It is a system of distributed servers that delivers content based on where the user is. Each region has edge locations, data centers that cache content from the origin server.

The redirect to a nearby copy happens during name resolution. Resolving a CDN URL directs the user to the nearest edge location, which serves the cached content. The origin server sees less load and the user gets content from a server that is physically close, so round trips are short. How DNS supports this kind of location-dependent answer is covered in [[networks/5-application/DNS|DNS]].

## Related notes

- [[networks/5-application/HTTP|HTTP]]
- [[networks/5-application/DNS|DNS]]
- [[networks/5-application/overview|application layer overview]]
