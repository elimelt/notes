---
title: Spring Boot Quickstart Guide
category: Software Engineering
tags: spring boot, quick start, spring web, rest repositories
description: A step-by-step guide to creating a Spring Boot application with Rest Repositories
---

# Quickstart

Create a zip file with (start.spring.io)[https://start.spring.io/] including the following dependencies:

- Spring Web
- Rest Repositories

## Unzip the file

```bash
unzip helloworld.zip
```

Open the project in IntelliJ. Start the server and verify that the application is running by visiting http://localhost:8080/hello

## Running the application

```bash
./gradlew bootRun
```

## Building the application

```bash
./gradlew build
```

## Deploying the application

```bash
./gradlew build
cp build/libs/<JAR_NAME>.jar <DEPLOYMENT_DIRECTORY>
```

