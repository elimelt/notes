---
title: Tokenization, Segmentation, and Edit Distance
category: Natural Language Processing
tags: tokenization, segmentation, edit distance, bpe, nltk, tr, regex, byte-pair encoding
description: Overview of tokenization techniques in Natural Language Processing (NLP), including Unix tools, regex, Byte-Pair Encoding (BPE), and edit distance.
---

# Tokenization

## Old-School Unix

```bash
# output all words in a file, one per line
tr -sc 'A-Za-z' '\n' < input.txt

# count the words in a file
tr -sc ’A-Za-z’ ’\n’ < input.txt | sort | uniq -c

# count the words in a file, case-insensitive
tr -sc 'A-Za-z' '\n' < input.txt | tr A-Z a-z | sort | uniq -c

# most frequent words
tr -sc 'A-Za-z' '\n' < input.txt | tr A-Z a-z | sort | uniq -c | sort -n -r
```

## Top-Down Regex Tokenization

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

BPE is a simple algorithm that learns tokens from a corpus by iteratively merging the most frequent pair of characters.

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

```python
import nltk

sent_text = nltk.sent_tokenize(text)

for sentence in sent_text:
    tokenized_text = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(tokenized_text)
    print(tagged)
```

## Edit Distance

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
