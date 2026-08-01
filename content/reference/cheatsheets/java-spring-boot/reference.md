---
title: Spring Boot Annotations
aliases:
  - cheatsheets/java-spring-boot/reference
category: Software Engineering
tags:
  - spring-boot
  - annotations
  - java
  - configuration
date: 2023-12-21
updated: 2026-07-30
status: draft
description: Quick reference for the core Spring Boot annotations used for configuration, component scanning, and request mapping.
sources:
  - title: Spring Boot Reference Documentation
    url: https://docs.spring.io/spring-boot/
    type: docs
---

Quick reference for the annotations I reach for when setting up a Spring Boot app. The [Spring Boot reference documentation](https://docs.spring.io/spring-boot/) covers the rest.

## Annotations

- `@SpringBootApplication`: marks the main class of the application. A combination of three other annotations: `@Configuration`, `@EnableAutoConfiguration`, and `@ComponentScan`.
- `@Configuration`: marks a class as a configuration class, which contains the bean definitions for the application context.
- `@EnableAutoConfiguration`: tells Spring Boot to start adding beans based on classpath settings, other beans, and various property settings.
- `@ComponentScan`: enables component scanning, letting Spring scan packages to find and configure beans.
- `@RestController`: marks a class as a controller where every method returns a domain object instead of a view. Shorthand for `@Controller` plus `@ResponseBody`.
- `@RequestMapping`: maps web requests onto specific handler classes and/or handler methods.
- `@RequestParam`: binds a web request parameter to a method parameter.

## Related

- [[software/java/collections-and-records|Creating Collections and Data Types in Modern Java]]
- [[reference/cheatsheets/java-spring-boot/running|Spring Boot Quickstart Guide]]
