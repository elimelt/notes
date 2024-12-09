# Creating Collections and Data Types in Modern Java

## Motivation

Often while testing your code or implementing common algorithms, you'll want to specify an immutable collection of elements. The UW intro series as (as far as I'm aware) doesn't teach you some pretty useful java features that can make this a lot easier.

Furthermore, java can be a little verbose when it comes to defining new data types to hold structured data. This is where the `record` keyword comes in.

## Arrays.asList

The most basic way to create a list in Java is to use the `Arrays.asList` method. This method takes a variable number of arguments and returns a fixed-size list backed by the specified array. This means that you can't add or remove elements from the list, but you can modify the elements themselves.

```java
List<Integer> list = Arrays.asList(1, 2, 3, 4, 5);
```

## Java 9+ Factory Methods

Java 9 introduced a new way to create immutable collections using factory methods. These methods are available in the `List`, `Set`, and `Map` interfaces. Here are some examples:

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

Records are a new feature in Java 14 that allow you to define simple data classes with minimal boilerplate. On top of being far more concise than traditional classes, records also provide a `toString`, `equals`, and `hashCode` method by default.

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

Now say we wanted to test our new `Card` object. We could do something like this:

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

  cards.stream()
    .sorted()
    .toList();

  assert cards.equals(expected);
}
```
