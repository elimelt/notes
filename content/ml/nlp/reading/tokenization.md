---
title: Tokenization, Segmentation, and Edit Distance
aliases:
  - natural-language-processing/reading/tokenization
category: Natural Language Processing
tags:
  - tokenization
  - segmentation
  - edit distance
  - bpe
  - nltk
  - tr
  - regex
  - byte-pair encoding
date: 2025-02-12
updated: 2026-07-30
status: draft
description: Ways to split text into tokens, from Unix one-liners and regex tokenizers to byte-pair encoding, plus sentence segmentation with NLTK and minimum edit distance.
sources:
  - title: Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)
    url: https://web.stanford.edu/~jurafsky/slp3/
    type: textbook
  - title: NLTK Book, ch. 3
    url: https://www.nltk.org/book/ch03.html
    type: book
---

## Purpose

A reference for splitting text into tokens, from Unix one-liners to byte-pair encoding, plus sentence segmentation and minimum edit distance. Mostly code I want to be able to grab quickly. Tokenization defines the terms consumed by [[ml/nlp/reading/information-retrieval|information retrieval]] systems and the model inputs used throughout [[ml/nlp/prompting|prompting]]. The material follows [SLP3](https://web.stanford.edu/~jurafsky/slp3/).

## Old-School Unix

A crude word tokenizer in one pipeline. `tr -sc 'A-Za-z' '\n'` squeezes every run of non-letters into a single newline, which puts one word per line. The rest is sorting and counting.

```bash
# output all words in a file, one per line
tr -sc 'A-Za-z' '\n' < input.txt

# count the words in a file
tr -sc 'A-Za-z' '\n' < input.txt | sort | uniq -c

# count the words in a file, case-insensitive
tr -sc 'A-Za-z' '\n' < input.txt | tr A-Z a-z | sort | uniq -c

# most frequent words
tr -sc 'A-Za-z' '\n' < input.txt | tr A-Z a-z | sort | uniq -c | sort -n -r
```

## Top-Down Regex Tokenization

Write the token grammar explicitly as alternations in a verbose regex and let NLTK apply it. This pattern (adapted from the [NLTK book, ch. 3](https://www.nltk.org/book/ch03.html)) handles abbreviations, hyphenated words, currency, percentages, and ellipses.

```python
import nltk

pattern = r'''(?x)     # set flag to allow verbose regexps
  (?:[A-Z]\.)+         # abbreviations, e.g. U.S.A.
| \w+(?:-\w+)*         # words with optional internal hyphens
| \$?\d+(?:\.\d+)?%?   # currency and percentages, e.g. $12.40, 82%
| \.\.\.               # ellipsis
| [.,;"'?():-_`]       # these are separate tokens
'''

text = "This is a sentence.  This is another sentence."
nltk.regexp_tokenize(text, pattern)
```

## Bottom-Up Tokenization with Byte-Pair Encoding (BPE)

BPE learns a vocabulary from a corpus by starting from single characters and repeatedly merging the most frequent adjacent pair. The learned merge list is the tokenizer, and tokenizing new text means replaying the merges in order.

```python
def get_freq(vocab: Dict[str, int]) -> Dict[Tuple[str, str], int]:
    pairs = defaultdict(int)
    for word, freq in vocab.items():
        symbols = word.split()
        for i in range(len(symbols)-1):
            pairs[symbols[i], symbols[i+1]] += freq
    return pairs
```

```python
def merge_vocab(pair: Tuple[str, str], vocab: Dict[str, int]) -> Dict[str, int]:
    bigram = ' '.join(pair)
    replacement = ''.join(pair)
    new_vocab = {}

    for word, freq in vocab.items():
        new_word = word.replace(bigram, replacement)
        new_vocab[new_word] = freq

    return new_vocab
```

```python
def bpe(C: List[str], k: int) -> List[Tuple[str, str]]:
    vocab = defaultdict(int)
    for word in C:
        spaced = ' '.join(word)
        vocab[spaced] += 1

    merges = []

    for i in range(k):
        pairs = get_freq(vocab)
        if not pairs:
            break

        best_pair = max(pairs.items(), key=lambda x: x[1])[0]
        merges.append(best_pair)
        vocab = merge_vocab(best_pair, vocab)

    return merges
```

In my experience, it doesn't start working well until you use a lot of data and a lot of merges. I've only tried once though, using ~100MB of text and 10,000 merges.

```python
corpus = ["low", "lowest", "newer", "wider", "new", "width"]
num_merges = 10

merge_operations = bpe(corpus, num_merges)

print("Merge operations performed:")
for i, pair in enumerate(merge_operations, 1):
    print(f"{i}. Merged '{pair[0]}' with '{pair[1]}'")
```

## Segmentation and Tokenization

NLTK's built-ins. Segment into sentences first, then tokenize and POS-tag the words within each sentence.

```python
import nltk

sent_text = nltk.sent_tokenize(text)

for sentence in sent_text:
    tokenized_text = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(tokenized_text)
    print(tagged)
```

## Edit Distance

The standard dynamic program. `dp[i][j]` is the edit distance between the first $i$ characters of `w1` and the first $j$ characters of `w2`, built up from insertions, deletions, and substitutions. This version charges 1 for every operation; SLP3 also presents a variant where substitution costs 2.

```python
def min_edit_distance(w1, w2):
    n, m = len(w1), len(w2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i

    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if w1[i - 1] == w2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return dp[n][m]
```

## Sources

- [Jurafsky & Martin, Speech and Language Processing (3rd ed. draft)](https://web.stanford.edu/~jurafsky/slp3/)
- [NLTK Book, ch. 3](https://www.nltk.org/book/ch03.html)
