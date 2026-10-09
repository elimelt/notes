---
title: Elijah Melton's Technical Notes
description: Elijah Melton's notes on algorithms, machine learning, recommender systems, LLM serving, software, hardware, and mathematics.
updated: 2026-10-09
authors:
  - elimelt
  - gpt-5.6-sol
  - gpt-6
---

Technical notes by Elijah Melton on algorithms, machine learning, systems,
software, hardware, and mathematics. I use this site to work through proofs,
papers, and implementation details that I want to be able to find again.

## Selected notes

- [[algorithms/greedy-algorithms|Why earliest finish time is optimal for interval scheduling]]: greedy-stays-ahead and exchange proofs, plus why interval partitioning sorts by start time instead.
- [[ml/nlp/decoding-strategies|Beam search, length normalization, and language-model decoding]]: the beam curse, greedy decoding, temperature, top-k, and nucleus sampling.
- [[ml/recommender-systems/deep-neural-networks-for-youtube-recommendations|Deep Neural Networks for YouTube Recommendations]]: candidate generation, ranking, sampled softmax, and watch-time objectives.
- [[ml/recommender-systems/predicting-clicks-on-ads-at-facebook|Practical Lessons from Predicting Clicks on Ads at Facebook]]: the GBDT plus logistic-regression model, data freshness, and online learning.
- [[ml/recommender-systems/two-tower-retrieval|Two-tower retrieval with a MovieLens experiment]]: an executable look at embedding retrieval and ranking.
- [[systems/operating-systems/benchmarks/store_fwd|Store-to-load forwarding benchmarks]]: a runnable x86 harness comparing exact-match, independent, and partially overlapping store/load pairs, with recorded setup and per-run timings.

## Browse by topic

- [[algorithms/index|Algorithms]]
- [[hardware/index|Hardware]]
- [[math/index|Mathematics]]
- [[ml/index|Machine learning]]
- [[software/index|Software engineering]]
- [[systems/index|Systems]]
- [[reference/index|Reference material]]

## About these notes

While in most cases I'd prefer reading the prose/thoughts of a fellow human,
these notes aren't for my own or anyone else's enjoyment, nor am I trying to
connect with anyone through my writing here. To be honest, I'm not even a great
writer, and have limited time to refine my thoughts and produce well-organized
and thoroughly cited works of literature.

At this point, I'd give ~90% of the credit to whatever frontier model polished
and organized my thoughts for presentation here ("co-authorship" according to
the git history...), and would describe myself as more of a reviewer/curator of
these notes than the actual author.

If you haven't built up a tolerance for AI slop, you might want to close this
tab now. If you're a student learning something for the first time and want a
rigorous and vetted introduction to a topic, I wouldn't look here. If your name
is Elijah Melton and you want a refresher on something you learned a half-decade
ago, then maybe these notes will be useful to you.

## What if it's wrong?!?

LLMs are wrong all the time, but the amount they're wrong has quickly trended
downward, and even seems to approach never when frontier models are anchored to
the truth by documents without errors. In 2026, I wholeheartedly expect my own
writing to contain more mistakes than most frontier models.

All that being said, yeah, there are probably a few errors here and there. I'd
expect the majority of them are caused either directly by my prompt, or by
errors in source documents I/the model cite. Still, any time I notice one, I
try to fix it. If you're the type of person that must right the wrong you
notice in the world, feel free to open a [PR](https://github.com/elimelt/notes)
to correct it.
