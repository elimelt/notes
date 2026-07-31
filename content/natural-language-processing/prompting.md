---
title: Prompting Language Models
category: Natural Language Processing
tags:
  - language-models
  - prompting
  - nlp
  - llm
date: 2025-03-10
updated: 2026-07-30
status: draft
description: Prompting techniques for language models, with small Python templates for few-shot prompting, retrieval-augmented generation, chain of thought, self-ask, and prompt self-improvement.
sources:
  - title: Brown et al. (2020), Language Models are Few-Shot Learners
    url: https://arxiv.org/abs/2005.14165
    type: paper
  - title: Wei et al. (2022), Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
    url: https://arxiv.org/abs/2201.11903
    type: paper
  - title: Press et al. (2022), Measuring and Narrowing the Compositionality Gap in Language Models
    url: https://arxiv.org/abs/2210.03350
    type: paper
  - title: Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
    url: https://arxiv.org/abs/2005.11401
    type: paper
  - title: Liu et al. (2023), Lost in the Middle - How Language Models Use Long Contexts
    url: https://arxiv.org/abs/2307.03172
    type: paper
  - title: Madaan et al. (2023), Self-Refine - Iterative Refinement with Self-Feedback
    url: https://arxiv.org/abs/2303.17651
    type: paper
---

## Purpose

A working reference for the prompt patterns I reach for most, each with a small Python template. Prompt behavior starts with how text gets split into tokens, so [[natural-language-processing/reading/tokenization|tokenization]] is useful background. Retrieval-augmented prompting builds on [[natural-language-processing/reading/information-retrieval|information retrieval]].

## Basic concepts

Where an instruction sits in the context matters. Models use information at the start and end of a long context more reliably than information buried in the middle ([Liu et al. 2023](https://arxiv.org/abs/2307.03172)), so put critical instructions near the end of the prompt, close to where generation begins.

Signal the response format you want through examples or explicit instructions. Format-by-example works best on base models, which complete text patterns. Chat-tuned models respond better to explicit formatting instructions, since instruction tuning trains them to follow directions.

Asking the model to adopt a persona ("You are an expert radiologist") steers tone and domain vocabulary. Treat it as a soft prior on style.

Few-shot prompting demonstrates the desired input-output mapping with examples before the real query. Large models can pick up a task from a handful of demonstrations with no gradient updates ([Brown et al. 2020](https://arxiv.org/abs/2005.14165)).

```python
prompt = lambda persona, context, query: \
f"""<Persona>
{persona}
</Persona>

<Context>
{context}
</Context>

<Query>
{query}
</Query>

<Response>
"""
```

## Retrieval augmented generation

Retrieve documents relevant to the query, then include them in the prompt so the model answers from provided evidence instead of parametric memory ([Lewis et al. 2020](https://arxiv.org/abs/2005.11401)). This grounds the response and gives you something to check its claims against.

```python
def rag_prompt(
  query, retrieved_contexts=[],
  instruction="Answer based on the provided context."
):
    context_section = "\n\n".join([
      f"Context {i+1}:\n{context}"
      for i, context in enumerate(retrieved_contexts)
    ])

    return f"""Retrieved Information:
    {context_section}

    Question: {query}

    {instruction}"""
```

## Chain of thought

Ask the model to reason step by step before answering. Requesting explicit intermediate reasoning improves accuracy on multi-step problems ([Wei et al. 2022](https://arxiv.org/abs/2201.11903)).

```python
def chain_of_thought_prompt(problem, steps_required=True):
    return f"""Problem: {problem}

{'Please think through this step-by-step and explain your reasoning for each step.' if steps_required else 'Solve this problem by showing your work.'}"""
```

## Self-ask

Have the model decompose a hard question into sub-questions, answer each in turn, and build toward the full answer. Press et al. ([2022](https://arxiv.org/abs/2210.03350)) introduced this format and showed the sub-questions give a natural place to plug in a search engine.

```python
def self_ask_prompt(question, allow_search_queries=True):
    return f"""Question: {question}

To solve this problem, I'll break it down into smaller questions and answer them one by one.

{'''If you need to search for specific information, format search queries as [SEARCH: your query].''' if allow_search_queries else ''}

Let me think through this carefully:"""
```

## Self improvement

Use the model to critique a prompt given the output it produced and the goal it missed, then generate a revised prompt. Iterating with model-generated feedback is the same loop as Self-Refine ([Madaan et al. 2023](https://arxiv.org/abs/2303.17651)).

```python
def self_improvement_prompt(original_prompt, model_output, goal):
    return f"""Original Prompt:
\"{original_prompt}\"

Output Received:
\"{model_output}\"

Desired Goal:
\"{goal}\"

What are the weaknesses of the original prompt? How could it be improved to better achieve the desired goal?

After analyzing the weaknesses, provide an improved version of the prompt."""
```

## Sources

- [Brown et al. (2020), Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)
- [Wei et al. (2022), Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)
- [Press et al. (2022), Measuring and Narrowing the Compositionality Gap in Language Models](https://arxiv.org/abs/2210.03350)
- [Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- [Liu et al. (2023), Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)
- [Madaan et al. (2023), Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
