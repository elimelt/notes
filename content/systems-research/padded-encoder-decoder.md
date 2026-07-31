---
title: Accelerating Padded Encoder-Decoder Transformer Models
category: Natural Language Processing
tags:
  - nlp
  - transformers
  - whisper
  - inference
  - systems research
date: 2025-03-10
updated: 2026-07-31
status: draft
description: Draft design note on pruning padded encoder tokens in Whisper-style encoder-decoder models.
sources:
  - https://cdn.openai.com/papers/whisper.pdf
  - https://github.com/openai/whisper
---

## Purpose

Record the design idea, implementation surface, and evaluation plan for pruning padded encoder tokens in Whisper-style models. This note does not include benchmark numbers yet, so it should be read as a research draft rather than a result report.

## Abstract

Encoder-decoder transformer models such as [Whisper](https://cdn.openai.com/papers/whisper.pdf) are often trained on fixed-length inputs. At inference time, that means a short audio clip still incurs encoder work for the full padded window. If the clip only contains a few seconds of speech, most of the encoder sequence consists of silence or padding tokens. Those tokens still participate in self-attention and still sit in the decoder's cross-attention context.

The idea in this note is to prune a contiguous region of padded encoder tokens before the transformer blocks run. The pruning rule keeps the span that contains real audio, then preserves a configurable amount of context around it. I have implementation sketches for two variants, one with a fixed padding margin and one with a percentage-based rule. What I do not have yet is a checked-in benchmark artifact, so I am intentionally avoiding speedup or accuracy claims here.

## Why this might help

Whisper's encoder processes a fixed token budget for each 30-second window. If a clip is much shorter than that, the wasted work grows with the padding region. Since encoder self-attention scales roughly as $O(n^2)$ in sequence length, removing even a few hundred useless tokens can save a meaningful amount of compute.

There is a catch. Padding is not always semantically dead. Attention near the content boundary can spill into nearby silent regions, and pruning too aggressively can damage downstream transcription quality. The practical question is not whether every padded token is useless. The practical question is whether there is a safe region far enough from real audio that cutting it buys latency without moving WER too much.

## Design

### Fixed-padding rule

Let the real audio occupy token indices $[s, e]$. Keep a fixed margin $m$ on either side and cut the middle padded block:

$$
[0, s - m) \cup (e + m, 1500)
$$

This rule is easy to reason about and gives predictable behavior across clips.

### Percentage-based rule

Let $p$ be the number of padded tokens in the sequence. Keep a fraction $\alpha p$ instead of a fixed margin:

$$
\text{tokens kept around content} \propto \alpha (1500 - \text{content length})
$$

This adapts the preserved padding budget to clip length. Short clips keep more absolute padding than a tiny fixed margin would allow, while long clips do not waste much capacity on extra context.

### Why prune before the transformer blocks

The cheapest place to intervene is after feature extraction and positional embedding, but before the encoder stack. That removes work from every downstream encoder layer and also shortens the sequence the decoder cross-attends to.

## Implementation Notes

The implementation surface is small:

- add an `AudioEncoderTokenPruner` module
- estimate or pass through the token count for real audio
- compute a cut region only when the removed span is large enough to matter
- preserve the original positional embeddings for the tokens that survive

The positional embedding part matters. If the surviving tokens are reindexed naively, the model sees a different positional layout than the one it was trained on. The safer move is to concatenate the original token slices and the matching positional slices:

```python
x_pruned = torch.cat((x[:, :cut_start, :], x[:, cut_end:, :]), dim=1)
pos_emb_pruned = torch.cat(
    (positional_embedding[:cut_start, :], positional_embedding[cut_end:, :]),
    dim=0,
)
```

I also want a minimum-cut threshold. If only a few tokens disappear, the pruning logic may cost more than it saves.

## Evaluation Plan

The old version of this note included placeholder numbers and figure callouts with no checked-in artifacts behind them. That is exactly the kind of thing these notes should avoid. The right next step is a reproducible evaluation pass.

### Measurements to collect

- wall-clock latency for end-to-end decoding
- encoder-only latency
- sequence length before and after pruning
- WER relative to the unmodified model
- the sensitivity of WER and latency to the pruning hyperparameters

### Experimental matrix

- Whisper base plus at least one larger variant
- one datacenter GPU and one resource-constrained edge device
- short, medium, and near-30-second clips from a public ASR dataset
- both fixed-padding and percentage-based pruning rules

### Artifacts still missing

- benchmark scripts
- raw timing tables
- WER reports
- attention heatmaps
- one end-to-end reproduction command

## Limits and Open Questions

The approach depends on estimating the real-audio span cleanly. Background noise, trailing silence, and clipping around the speech boundary can all make that harder than it sounds. The idea is also model-specific in its current form. Whisper is the motivating case, but other encoder-decoder models may place useful attention in different regions.

The main open question is simple: for which clip lengths does pruning remain net-positive once decoder work and host overhead are included?

## Conclusion

The core idea still seems worth testing because the wasted computation comes directly from fixed-length padding, not from a narrow quirk of one implementation. What this note needs next is evidence, not more exposition. Once the measurements and figures exist in the repo, the draft can become a proper result write-up.

## Related

- [[systems-research/sparsity-notes|Faster Causal Self Attention]]
