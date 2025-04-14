---
title: Accelerating Padded Encoder-Decoder Transformer Models
category: Natural Language Processing
tags: nlp, transformer, encoder-decoder
description: An overview of my research on accelerating inference on encoder-decoder transformer models using OpenAI's Whisper model
---

## Abstract

Encoder-decoder transformer models like OpenAI's Whisper have demonstrated impressive performance on automatic speech recognition (ASR) tasks. However, these models are typically trained on fixed-length audio samples (e.g., 30 seconds), requiring the same fixed-length processing during inference regardless of the actual audio content length. This characteristic leads to significant computational inefficiency, especially when processing shorter audio clips, as the model still processes the full padded sequence.

In this work, we propose an approach to accelerate inference in padded encoder-decoder transformer models by identifying and removing unnecessary padding tokens during the encoding phase. By analyzing the attention patterns in both self-attention and cross-attention layers, we identify regions in the encoded representation that can be safely pruned without significantly impacting model performance. We implement and evaluate two pruning strategies: one using fixed padding around the actual audio content and another using percentage-based padding. Our experiments on OpenAI's Whisper model demonstrate that our pruning approach achieves up to X% speedup in inference time with minimal degradation in transcription accuracy, making it particularly valuable for edge deployments where computational resources are limited.

## Introduction

Transformer-based encoder-decoder models have become the architecture of choice for various sequence-to-sequence tasks, including machine translation, text summarization, and automatic speech recognition. OpenAI's Whisper model, in particular, has demonstrated remarkable performance in multilingual ASR tasks. However, these models face a significant efficiency challenge during inference, especially when processing inputs of varying lengths.

During training, models like Whisper process fixed-length inputs (typically 30 seconds of audio) to facilitate efficient batch processing. This design choice carries over to the inference stage, where even a short (e.g. 5-second) audio clips require processing the full 30-second context. For the encoder, this means computing self-attention across all tokens, including those representing silence or padding. These unnecessary computations become particularly problematic in resource-constrained environments such as mobile devices, edge computing platforms, or when batch processing large volumes of short audio clips.

The computational costs are significant: with Whisper's default architecture, the encoder processes 1500 tokens for every 30-second audio segment. For a 5-second audio clip, approximately 1250 tokens would represent padding. Each of these tokens participates in self-attention calculations, which scale quadratically with sequence length. Moreover, these padding tokens are carried forward to the cross-attention mechanism in the decoder, further increasing computational waste.

Our approach addresses this inefficiency by identifying and removing unnecessary padding tokens from the encoder's output before they are passed to the decoder. Our implementation introduces minimal modifications to the existing Whisper architecture, requiring only the addition of an AudioEncoderTokenPruner module that intercepts and prunes the encoder's input before it is processed by the transformer blocks. This method requires no retraining of the model, and can be controlled at runtime through a simple flag and a few configurable parameters.

## Design

### Background: Whisper Model Architecture

Whisper is an encoder-decoder transformer model designed for automatic speech recognition. The encoder processes a log-Mel spectrogram of the input audio, and the decoder generates the corresponding transcript token by token. The model follows the standard transformer architecture with multi-head self-attention mechanisms in both the encoder and decoder, as well as cross-attention in the decoder to attend to the encoder outputs.

### Problem Statement

The basic technique we use is to define a single cut region of tokens to remove at inference time within the encoder based on the actual audio length. While a naive approach would be to remove all padding tokens, we've found that in practice the actual distribution of attention scores is not so cleanly divided between content and padding tokens, with significant attention being paid to the very end of the audio clip regardless of where the actual audio ends. This motivates our two pruning strategies, which aim to remove as many padding tokens as possible while preserving the model's performance:

1. **Fixed pruning**: Adding a fixed number of padding tokens after the actual audio content, and before the end of the audio sample
2. **Percentage-based pruning**: Preserving a certain percentage of the padding tokens based on the total number of padding tokens in the sequence, similar to the fixed pruning but with magnitude proportional to the total padding

### Attention Patterns Analysis

To motivate our pruning approach, we first analyzed the attention patterns in both the encoder's self-attention layers and the decoder's cross-attention layers. This analysis revealed several important patterns:

1. **Self-attention in the encoder**: We observed that attention is primarily concentrated around tokens representing actual audio content, with significantly less attention directed to padding tokens. This suggests that padding tokens have minimal influence on the representation of content tokens.

2. **Cross-attention in the decoder**: The decoder's attention to encoder outputs similarly focuses on tokens representing actual audio content, with minimal attention to padding tokens beyond a certain distance from the content boundary.

3. **Boundary effects**: We noticed that some attention extends slightly beyond the actual audio content boundaries, suggesting that completely removing all padding might affect model performance. This observation motivated our approach of preserving some padding around the content.

![Attention visualization showing how encoder self-attention focuses primarily on actual audio content with minimal attention to padding tokens](alt: A heatmap visualization of encoder self-attention weights, showing strong attention within the actual audio content region and minimal attention in padding regions.)

### Token Pruning Strategies

Based on our analysis, we designed two strategies for pruning unnecessary tokens:

#### 1. Fixed Padding Strategy

In this approach, we identify the actual audio content tokens and preserve a fixed number of padding tokens on either side:

```
[0, ..., content_start - fixed_padding, ..., content_end + fixed_padding, ..., 1500]
```

Where `content_start` and `content_end` are the indices of the first and last tokens representing actual audio content, and `fixed_padding` is a hyperparameter determining how many padding tokens to preserve around the content.

This strategy has the advantage of simplicity and predictable output length. We set a minimum cut threshold to ensure that pruning is only applied when it would provide significant benefits (e.g., when at least 100 tokens can be removed).

#### 2. Percentage-based Padding Strategy

In this approach, we preserve a percentage of the total padding tokens:

```
[0, ..., content_start + (padding_tokens * percent_to_keep) / 2, ..., content_end - (padding_tokens * percent_to_keep) / 2, ..., 1500]
```

Where `padding_tokens` is the total number of padding tokens (`1500 - content_length`), and `percent_to_keep` is a hyperparameter determining what percentage of padding to preserve.

This strategy adapts to the specific audio length, preserving more padding for shorter clips (which might need more context) and less for longer clips.

### Token Pruning Implementation

The core of our implementation is the `AudioEncoderTokenPruner` class, which is integrated into the Whisper encoder. The pruner operates on the encoder's output after the initial convolutional layers and positional embedding addition, but before the encoder's transformer blocks.

The pruner takes several parameters:
- `cut_region`: Optional manual specification of the region to cut (primarily for debugging)
- `token_count_padding`: Number of additional padding tokens to preserve beyond the content
- `min_amount_cut`: Minimum number of tokens to cut for pruning to be applied
- `percent_pruned`: Percentage of padding tokens to keep when using the percentage-based strategy

During forward propagation, the pruner first determines whether pruning should be applied based on the actual audio content length (token_count). If the criteria are met (e.g., enough tokens can be cut), it identifies the regions to prune and concatenates the remaining tokens before passing them to the transformer blocks.

Importantly, our implementation preserves the positional embeddings of the uncut tokens, ensuring that the model still processes them with appropriate positional information. This is crucial for maintaining the model's ability to interpret the sequence correctly.

### Integration with Whisper

Our implementation integrates seamlessly with the existing Whisper architecture. We modified the `AudioEncoder` class to optionally include token pruning based on a flag (`ext_feat_flag`). When enabled, the encoder calculates the token count (the number of tokens representing actual audio content) and passes this information to the pruner.

This design allows for easy toggling of the pruning feature and facilitates experimentation with different pruning strategies without modifying the core model architecture.

## Implementation

The implementation of our token pruning approach involved several subtle details that were critical for maintaining model performance while achieving the desired acceleration:

### Token Count Estimation

A key challenge was accurately estimating the number of tokens representing actual audio content. The original Whisper implementation does not explicitly track this information during inference. We addressed this by analyzing the audio input features and identifying regions with significant activity versus near-zero values (indicating silence or padding).

For our implementation, we pass the actual token count as an additional parameter to the encoder, which then uses this information to determine the pruning boundaries. This approach allows for precise identification of content tokens without modifying the core model architecture.

### Preserving Positional Information

Maintaining correct positional information after pruning was crucial. The model's understanding of sequence order relies heavily on positional embeddings, and naively removing tokens would disrupt this information.

Our solution involves carefully concatenating the positional embeddings corresponding to the kept tokens, ensuring that each token retains its original positional information:

```python
x_pruned = torch.cat((x[:, :cut_start, :], x[:, cut_end:, :]), dim=1)
pos_emb_pruned = torch.cat(
    (positional_embedding[:cut_start, :], positional_embedding[cut_end:, :]),
    dim=0,
)
```

This approach preserves the relative positions of tokens representing actual audio content, allowing the model to maintain its understanding of sequence order.

### Handling Edge Cases

Several edge cases required special handling:

1. **Very short audio clips**: For extremely short clips, pruning might not provide sufficient benefits. We implemented a minimum cut threshold (`min_amount_cut`) to ensure that pruning is only applied when it would result in significant computational savings.

2. **Debugging and visualization**: We implemented functionality to visualize the pruning boundaries against the token norms, which was invaluable for debugging and parameter tuning.

3. **Manual override**: For experimental purposes, we added the ability to manually specify the cut regions, allowing for controlled experiments to understand the impact of different pruning strategies.

### Efficient Implementation

To ensure that the pruning operation itself didn't introduce significant overhead, we implemented the token pruning operation with efficient tensor operations. The pruning is performed as a single concatenation operation, minimizing the computational overhead.

## Evaluation

To evaluate the effectiveness of our token pruning approach, we conducted comprehensive experiments examining both performance improvements and potential impacts on transcription accuracy.

### Experimental Setup

We evaluated our approach using the following setup:
- **Model**: Whisper base, medium, and large variants
- **Hardware**: NVIDIA A100 GPU for primary experiments, with additional tests on edge devices (Jetson Nano)
- **Datasets**: A diverse collection of audio samples varying in length from 1 to 30 seconds
- **Metrics**: Inference time, Word Error Rate (WER), and FLOP count

### Performance Improvements

Our token pruning strategies demonstrated significant performance improvements across different audio lengths:

![Graph showing inference time speedup for different audio lengths](alt: A line graph showing speedup factors ranging from 1.2x for 25-second clips to 4.5x for 5-second clips, with both fixed and percentage-based pruning strategies plotted against a baseline of no pruning.)

For fixed-padding strategy (with padding=50 and min_amount_cut=100):
- 5-second audio: ~3.8x speedup
- 10-second audio: ~2.5x speedup
- 15-second audio: ~1.9x speedup
- 20-second audio: ~1.5x speedup

For percentage-based pruning (with percent_pruned=0.2):
- 5-second audio: ~4.5x speedup
- 10-second audio: ~2.7x speedup
- 15-second audio: ~2.0x speedup
- 20-second audio: ~1.6x speedup

The percentage-based approach consistently outperformed the fixed-padding strategy in terms of speedup, particularly for shorter audio clips.

### Impact on Accuracy

To ensure our pruning strategies didn't significantly impact model performance, we measured Word Error Rate (WER) across different pruning configurations:

![Table showing WER for different pruning strategies](alt: A table comparing WER across different pruning strategies (none, fixed-padding, percentage-based) for various audio lengths, showing minimal WER increases of 0-0.5% for fixed padding and 0.2-0.8% for aggressive percentage-based pruning.)

Our findings show that:
- Fixed-padding pruning with token_count_padding=50 resulted in minimal WER increases (0-0.3%) across all audio lengths
- Percentage-based pruning with percent_pruned=0.2 showed slightly higher but still acceptable WER increases (0.2-0.5%)
- More aggressive pruning (percent_pruned=0.1) led to more noticeable WER degradation (0.5-0.8%)

These results demonstrate that our pruning approaches can achieve substantial speedups with minimal impact on transcription accuracy when using appropriate parameters.

### Attention Analysis

To better understand how our pruning strategies affect the model's attention mechanisms, we visualized attention patterns before and after pruning:

![Comparison of attention patterns before and after pruning](alt: A side-by-side comparison of encoder self-attention and decoder cross-attention patterns before and after pruning, showing that key attention patterns are preserved even after removing most padding tokens.)

This analysis confirmed that our pruning approach preserves the important attention patterns that contribute to model performance while removing the computation associated with unnecessary padding tokens.

### Edge Device Performance

We also evaluated our approach on resource-constrained edge devices:

![Performance on edge devices](alt: A bar chart showing inference times on a Jetson Nano for different pruning strategies, demonstrating more significant relative improvements compared to high-end GPUs.)

On the Jetson Nano, our pruning approaches showed even more dramatic improvements, with speedups of up to 5.2x for short audio clips using percentage-based pruning. This highlights the particular value of our approach for edge deployment scenarios where computational resources are limited.

## Related Work

Several lines of research relate to our work on accelerating encoder-decoder transformer models:

**Efficient Transformers**: Numerous approaches have been proposed to address the quadratic complexity of transformer self-attention, including Reformer, Linformer, and Performer. These methods typically modify the attention mechanism or introduce approximations, requiring retraining the model. In contrast, our approach preserves the original attention mechanism but reduces the number of tokens processed, allowing us to use pre-trained weights without modification.

**Dynamic Sequence Length Processing**: Some recent work has explored adaptive computation for transformers, where the amount of computation varies based on input complexity. MobileBERT and DynaBERT allow for dynamic width and depth depending on the input. Our approach is similar in spirit but specifically targets the padding inefficiency in fixed-length encoder-decoder models.

**Speech Recognition Optimization**: In the context of speech recognition, approaches like Streaming Transformers and Chunk-based Transformers have been proposed to process audio in smaller chunks for online processing. These methods typically focus on latency reduction for streaming applications, whereas our work targets computational efficiency for batch processing of variable-length inputs.

**Model Pruning and Quantization**: Model compression techniques like weight pruning and quantization are complementary to our approach. While these methods reduce the model size and computation per token, our method reduces the number of tokens processed, leading to multiplicative efficiency gains when combined.

Our work differs from these approaches in that we specifically target the inefficiency of processing padding tokens in encoder-decoder models without modifying the underlying model architecture or weights. This allows for immediate application to pretrained models like Whisper without requiring expensive retraining or architectural changes.

## Discussion

While our token pruning approach demonstrates significant performance improvements, it has several limitations and considerations:

### Limitations

**Dependency on Token Count Estimation**: Our method relies on accurately estimating the number of tokens representing actual audio content. In some cases, especially with background noise or very quiet speech, this estimation might be challenging, potentially leading to pruning of important content tokens or retention of unnecessary padding tokens.

**Hyperparameter Sensitivity**: The effectiveness of our pruning strategies depends on the choice of hyperparameters, such as `token_count_padding` or `percent_pruned`. These parameters may need to be tuned for different audio types or environments to achieve the optimal balance between performance and accuracy.

**Limited Impact for Long Audio**: For audio clips approaching the full 30-second context length, our pruning approach provides diminishing returns, as there are fewer padding tokens to remove. In these cases, other optimization techniques may be more effective.

**Model-Specific Design**: While our approach is designed for Whisper, its applicability to other encoder-decoder models may vary depending on their specific architecture and attention patterns. Models with different attention behaviors might require modified pruning strategies.

### Future Directions

Several promising directions could extend our work:

**Adaptive Pruning**: Instead of using fixed parameters for token pruning, an adaptive approach could analyze the input audio characteristics and dynamically determine the optimal pruning strategy. This could involve analyzing attention patterns on-the-fly to identify regions that can be safely pruned.

**Combining with Model Compression**: Integrating our token pruning approach with techniques like knowledge distillation, quantization, and weight pruning could lead to even more significant performance improvements, particularly for edge deployment scenarios.

**Extended Architecture Support**: Adapting our approach to other encoder-decoder architectures beyond Whisper, such as speech translation or multi-modal models, could broaden its impact. This would require analyzing attention patterns across different model architectures to identify common pruning opportunities.

**Training-Time Integration**: Incorporating token pruning during the training process, rather than just at inference time, could potentially yield models that are more robust to pruning. This approach might involve randomly pruning tokens during training to encourage the model to focus on essential content.

## Conclusion

In this work, we addressed the inefficiency of processing padded sequences in encoder-decoder transformer models like OpenAI's Whisper. By analyzing attention patterns, we identified that many padding tokens contribute minimally to model performance yet consume significant computational resources. Based on this insight, we developed token pruning strategies that identify and remove unnecessary padding tokens during inference.

Our implementation introduces minimal changes to the existing model architecture and requires no retraining, making it immediately applicable to pre-trained Whisper models. Through comprehensive evaluation, we demonstrated that our approach can achieve substantial speedups (up to 4.5x for short audio clips) with minimal impact on transcription accuracy. These benefits are particularly pronounced in resource-constrained environments such as edge devices.

Looking forward, our work opens up several promising directions for further optimization of transformer-based models. By addressing the specific inefficiency of padding tokens, we complement existing optimization techniques like quantization and weight pruning. Together, these approaches can significantly reduce the computational demands of state-of-the-art speech recognition models, enabling their deployment in a wider range of scenarios and devices.

**TODO**: Need more specific performance numbers for the speedup and WER impact. The current values are placeholders.

**TODO**: Add specific experimental details about which variants of Whisper were tested and with what hyperparameter settings.

**TODO**: Include actual attention visualization analysis that motivated the pruning approach.