---
title: Spring Boot Quickstart Guide
aliases:
  - cheatsheets/java-spring-boot/running
category: Software Engineering
tags:
  - spring-boot
  - quickstart
  - gradle
  - spring-web
date: 2023-12-21
updated: 2026-07-30
status: evergreen
description: Steps to generate, run, build, and deploy a Spring Boot application with Gradle.
sources:
  - title: Spring Initializr
    url: https://start.spring.io/
    type: docs
---

Minimal steps to get a Spring Boot project running with Gradle.

## Create the project

Generate a zip at [start.spring.io](https://start.spring.io/) including the following dependencies:

- Spring Web
- Rest Repositories

Unzip the file and open the project in IntelliJ:

```bash
unzip helloworld.zip
```

## Running the application

```bash
./gradlew bootRun
```

The server listens on http://localhost:8080 once it boots.

## Building the application

```bash
./gradlew build
```

## Deploying the application

```bash
./gradlew build
cp build/libs/<JAR_NAME>.jar <DEPLOYMENT_DIRECTORY>
```

## Related

- [[reference/cheatsheets/java-spring-boot/reference|Spring Boot Annotations]]
