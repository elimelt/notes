---
title: Creating Collections and Data Types in Modern Java
aliases:
  - teaching/modern-java/collections-and-records
category: Software Engineering
tags:
  - java
  - collections
  - immutability
  - java records
date: 2024-12-08
updated: 2026-07-30
status: evergreen
description: Creating immutable collections with Arrays.asList and the Java 9 factory methods, and defining data types with records.
sources:
  - title: "JEP 269: Convenience Factory Methods for Collections"
    url: https://openjdk.org/jeps/269
    type: docs
  - title: "JEP 395: Records"
    url: https://openjdk.org/jeps/395
    type: docs
---

## Motivation

Often while testing your code or implementing common algorithms, you'll want to specify an immutable collection of elements. The UW intro series (as far as I'm aware) doesn't teach some pretty useful Java features that make this a lot easier.

Java is also verbose when it comes to defining new data types to hold structured data. The `record` keyword fixes that.

## Arrays.asList

The most basic way to create a list in Java is the `Arrays.asList` method. It takes a variable number of arguments and returns a fixed-size list backed by the underlying array. You can't add or remove elements, but you can modify the elements themselves.

```java
List<Integer> list = Arrays.asList(1, 2, 3, 4, 5);
```

## Java 9+ Factory Methods

Java 9 introduced factory methods for creating immutable collections ([JEP 269](https://openjdk.org/jeps/269)). They're available on the `List`, `Set`, and `Map` interfaces:

```java
List<Integer> list = List.of(1, 2, 3, 4, 5);
Set<Integer> set = Set.of(1, 2, 3, 4, 5);
Map<Integer, String> map = Map.of(
  1, "one",
  2, "two",
  3, "three"
);
```

## Records

Records let you define simple data classes with minimal boilerplate. They shipped as a preview in Java 14 and became standard in Java 16 ([JEP 395](https://openjdk.org/jeps/395)). On top of being far more concise than traditional classes, records provide `toString`, `equals`, and `hashCode` methods by default.

```java
// With classes
class Point {
  int x;
  int y;

  Point(int x, int y) {
    this.x = x;
    this.y = y;
  }

  public String toString() {
    return String.format("(%d, %d)", x, y);
  }

  public boolean equals(Object o) {
    if (o == this) return true;
    if (!(o instanceof Point)) return false;
    Point p = (Point) o;
    return p.x == x && p.y == y;
  }

  public int hashCode() {
    return Objects.hash(x, y);
  }
}

// With records
record Point(int x, int y) {}
```

## Using this in Practice

Say we're implementing a poker game and we want to represent a card. With introductory Java knowledge, you might define a class like this:

```java
enum Suit {
  HEARTS, DIAMONDS, CLUBS, SPADES
}

class Card {
  private final Suit suit;
  private final int rank;

  Card(Suit suit, int rank) {
    this.suit = suit;
    this.rank = rank;
  }

  public Suit getSuit() {
    return suit;
  }

  public int getRank() {
    return rank;
  }

  public String toString() {
    return String.format("%d of %s", rank, suit);
  }

  public boolean equals(Object o) {
    if (o == this) return true;
    if (!(o instanceof Card)) return false;
    Card c = (Card) o;
    return c.suit == suit && c.rank == rank;
  }

  public int hashCode() {
    return Objects.hash(suit, rank);
  }
}
```

With records, you can define the same class in a much more concise way:

```java
enum Suit {
  HEARTS, DIAMONDS, CLUBS, SPADES
}

record Card(Suit suit, int rank) {}
```

We can even add methods to records, like so:

```java
record Card(Suit suit, int rank) implements Comparable<Card> {
  public int compareTo(Card other) {
    return Integer.compare(rank, other.rank);
  }
}
```

Now say we wanted to test our new `Card` object:

```java
public static void main(String[] args) {
  var cards = List.of(
    new Card(Suit.CLUBS, 4),
    new Card(Suit.DIAMONDS, 3),
    new Card(Suit.HEARTS, 2),
    new Card(Suit.SPADES, 5)
  );

  var expected = List.of(
    new Card(Suit.HEARTS, 2),
    new Card(Suit.DIAMONDS, 3),
    new Card(Suit.CLUBS, 4),
    new Card(Suit.SPADES, 5)
  );

  var sorted = cards.stream()
    .sorted()
    .toList();

  assert sorted.equals(expected);
}
```

The sort has to produce a new list, since `List.of` gives us an immutable one. The comparison works because `Card` implements `Comparable`, and the equality check works because records generate `equals` for us. Run with `java -ea` so the assert actually fires.

## Related

- [[software/java/lambdas-and-streams|A Soft Introduction to Java Streams and Lambdas]]
