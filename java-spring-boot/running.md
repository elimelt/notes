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

