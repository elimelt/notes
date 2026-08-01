---
title: Natural Language Processing
category: Natural Language Processing
tags:
  - nlp
  - tokenization
  - classification
  - neural networks
date: 2026-07-31
updated: 2026-07-31
status: evergreen
description: Overview of the NLP notes, from tokenization and linear classifiers to neural models and prompting.
---

## Purpose

These notes cover the basic pipeline for turning text into something a model can work with. Start with [[ml/nlp/reading/tokenization|tokenization]], then move to [[ml/nlp/reading/classification|classification]] and [[ml/nlp/reading/multinomial-logistic-regression|multinomial logistic regression]]. [[ml/nlp/reading/neural-networks|Neural networks]] shows what changes once linear decision boundaries stop being enough.

The section also holds practical notes that sit closer to modern language models than to textbook NLP. [[ml/nlp/prompting|Prompting]] is the bridge between the older modeling material and the newer model-facing workflow.

## Suggested path

- Represent text: [[ml/nlp/reading/tokenization|tokenization]], [[ml/nlp/ppmi|PPMI]], [[ml/nlp/reading/information-retrieval|information retrieval]]
- Build classifiers: [[ml/nlp/reading/classification|classification]], [[ml/nlp/reading/multinomial-logistic-regression|multinomial logistic regression]]
- Add nonlinear models: [[ml/nlp/reading/neural-networks|neural networks]]
- Use current models: [[ml/nlp/prompting|prompting]]

## Related notes

- [[deep-learning/character-level-rnn-on-wikitext-2|Character-Level RNN on WikiText-2]]
