---
title: Prompting Language Models
category: Natural Language Processing
tags: language-models, prompting, nlp, llm
description: All about prompting language models.
---

## Basic Concepts

- **Recency Effect**: Place critical instructions at the end of your prompt where they'll have the strongest impact.
- **Output Formatting**: Signal your expected response format through examples or explicit instructions. This doesn't work as well for chat-based models, since they're designed outside of the scope of basic auto-completion.
- **Persona Invocation**: Direct the model to adopt a specific expertise or perspective.
- **Few-Shot Learning**: Demonstrate desired outputs through examples before asking for a new response.

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

## Retrieval Augmented Generation

Enhance model responses by providing relevant external information:

- Retrieve pertinent documents or data based on the query.
- Incorporate this context into the prompt to ground the model's response in factual information.

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

## Chain of Thought

Guide the model through complex reasoning:

- Break down problems into logical steps.
- Encourage methodical thinking by requesting explicit reasoning.

```python
def chain_of_thought_prompt(problem, steps_required=True):
    return f"""Problem: {problem}

{'Please think through this step-by-step and explain your reasoning for each step.' if steps_required else 'Solve this problem by showing your work.'}"""
```

## Self-Ask

Enable recursive problem-solving:

- Instruct the model to decompose complex problems by asking itself sub-questions.
- Allow it to answer these questions sequentially to build toward a complete solution.

```python
def self_ask_prompt(question, allow_search_queries=True):
    return f"""Question: {question}

To solve this problem, I'll break it down into smaller questions and answer them one by one.

{'''If you need to search for specific information, format search queries as [SEARCH: your query].''' if allow_search_queries else ''}

Let me think through this carefully:"""
```

## Self Improvement

Create a feedback loop for prompt optimization:

- Use the model to evaluate the effectiveness of existing prompts.
- Incorporate this critique as context for generating improved versions.

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
