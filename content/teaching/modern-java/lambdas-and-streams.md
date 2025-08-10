---
title: A Soft Introduction to Java Streams and Lambdas
category: Software Engineering
tags: java, streams, lambdas, functional programming, declarative programming, collections, filtering, iteration
description: Covers the implementation of Java Streams and Lambdas, two key features that enable functional and declarative programming in Java. Discusses the motivation for these constructs, their usage in common operations like filtering, mapping, aggregation, and grouping of data from Java collections. Provides a high-level overview of the core concepts and capabilities of Streams and Lambdas, highlighting their role in simplifying complex data processing tasks in a concise and expressive manner.
---

# A Soft Introduction to Java Streams and Lambdas

## Motivation

If you've been programming in Java for a while (perhaps you're coming out of the 12x/14x series at UW), you're probably familiar with the regular *imperative* style of programming using loops and conditionals. There's nothing wrong with this, but often times, you'll find yourself writing a lot of code for simple operations.

For example, consider the following code snippet:

```java
List<User> getAdmins(List<User> users) {
    List<User> admins = new ArrayList<>();
    for (User user : users) {
        if (user.isAdmin()) {
            admins.add(user);
        }
    }
    return admins;
}
```

At a high level, we iterate over the provided list of users, and filter for those that are admins.

Perhaps you're also trying to make sure that *all* users are admins:

```java
boolean allAdmins(List<User> users) {
    for (User user : users) {
        if (!user.isAdmin()) {
            return false;
        }
    }
    return true;
}
```

You've probably written similar code snippets hundreds of times. To reiterate, there's nothing wrong with this style of programming, but for a relatively simple operation, you're writing a lot of code.

What's arguably better is to use a more *declarative* style of programming. This is where Java Streams and Lambdas come in.

## Java Streams

Java Streams are in some way similar to Iterators, but with a lot more functionality. They allow you to perform operations on a collection of elements in a more compositional way. For example, consider the following code snippet:

```java
List<User> admins = users.stream()
    .filter(user -> user.isAdmin())
    .collect(Collectors.toList());

// note while using collect(Collectors.to*()) is going to work in most cases,
// when terminating a stream to a list you can also use the toList() method
List<User> admins = users.stream().filter(User::isAdmin).toList();
```

There's a lot going on here, I know. Let's break it down:

- `users.stream()`: This converts the list of users into a Stream (`java.util.stream.Stream`).
- `user -> user.isAdmin()`: This is a Lambda expression. It's a way of passing a function as an argument. In this case, we're passing a function that takes a `User` object and returns a boolean. Alternatively, you could write this as `User::isAdmin`, meaning we call the `isAdmin` method on the `User` object passed in as an argument.
- `filter(...)`: This is an intermediate operation. It takes a predicate (a function that returns a boolean) and filters out elements that don't satisfy the predicate.
- `collect(...)`: This is a terminal operation. It collects the elements of the Stream into a list.

## Lambdas

Lambdas are a way of defining functions without having to explicitly define a class or method. They're particularly useful when you want to pass a function as an argument to another function. Here are some different ways you can use lambdas:

```java
// A lambda that takes no arguments and returns void
Runnable r = () -> System.out.println("Hello, world!");

// A lambda that takes two integers and returns an integer
BiFunction<Integer, Integer, Integer> add = (a, b) -> a + b;

// A lambda that takes a string and returns a string
Function<String, String> toUpperCase = s -> s.toUpperCase();

// A lambda that takes a string and returns a boolean
Predicate<String> isEmpty = s -> s.isEmpty();
```

Luckily, you don't need to remember all of these interfaces. More often than not, you're going to define lambdas without ever assigning them to a variable. In cases where you do need to assign them to a variable, you can use the `var` keyword.

## Common Operations

Here are some examples of iterative vs. stream-based operations:

### Filtering

```java
// Imperative
List<User> admins = new ArrayList<>();
for (User user : users) {
    if (user.isAdmin()) {
        admins.add(user);
    }
}

// Declarative
List<User> admins = users.stream()
    .filter(User::isAdmin)
    .toList();
```

### Mapping

```java
// Imperative
List<String> names = new ArrayList<>();
for (User user : users) {
    names.add(user.getName());
}

// Declarative
List<String> names = users.stream().map(User::getName).toList();
```

### All match

```java
// Imperative
boolean allAdmins = true;
for (User user : users) {
    if (!user.isAdmin()) {
        allAdmins = false;
        break;
    }
}

// Declarative
boolean allAdmins = users.stream().allMatch(User::isAdmin);
```

### Any match

```java
// Imperative
boolean anyAdmins = false;
for (User user : users) {
    if (user.isAdmin()) {
        anyAdmins = true;
        break;
    }
}

// Declarative
boolean anyAdmins = users.stream().anyMatch(User::isAdmin);
```

### Sum

```java
// Imperative
int sum = 0;
for (int i : numbers) {
    sum += i;
}

// Declarative
int sum = numbers.stream().reduce(0, Integer::sum);

// alternatively, you can use the sum() method
int sum = numbers.stream().mapToInt(Integer::intValue).sum();

// or Collectors.summingInt()
int sum = numbers.stream().collect(Collectors.summingInt(Integer::intValue));

```

### Grouping

```java
// Imperative
Map<String, List<User>> usersByRole = new HashMap<>();
for (User user : users) {
    usersByRole.computeIfAbsent(
      user.getRole(), k -> new ArrayList<>()
    ).add(user);
}

// Declarative
Map<String, List<User>> usersByRole = users.stream()
    .collect(Collectors.groupingBy(User::getRole));
```

