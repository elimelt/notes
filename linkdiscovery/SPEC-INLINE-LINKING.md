# Implementation Spec: A Learned Inline-Link Discovery System for a Personal Technical Knowledge Base

## TL;DR
- **Formulate this as a staged, closed-world *mention-plus-entity-linking* pipeline with an explicit no-link (rejection) option — not relation extraction and not a single joint model.** Your working hypothesis (Markdown-aware span proposal → learned naturalness scorer → dense target retrieval → cross-encoder/late-interaction reranker → calibrated no-link → sparse global selection) is well-aligned with the literature (BLINK, Kolitsas et al., Wikimedia add-a-link) and is the right architecture. The main correction: **do the data audit and build a small expert benchmark *first*, keep the encoder frozen for v1, and treat unlinked spans with positive-unlabeled discipline, not as clean negatives.**
- **Set a realistic first-release bar of precision@1 ≈ 0.75–0.80 on reviewed proposals at a deliberately low recall (~40%), mirroring the deployed Wikimedia add-a-link model**, and enforce a per-note link budget because useful links are rare and compete for reader attention.
- **Wikipedia pretraining is worth doing only for the mention/naturalness (keyphraseness) head, not the target linker** — your targets are private notes, not Wikipedia entities. In-domain weak supervision from titles/aliases/headings plus a frozen Qwen3 encoder is enough to reach a reviewable v1; defer Wikipedia transfer to an ablation.

## Key Findings

1. **The task is genuinely multitask but should be *staged, not jointly trained*, at your scale.** The canonical decomposition is Mention Detection (MD) + Entity Disambiguation/Linking (ED). Kolitsas, Ganea & Hofmann ("End-to-End Neural Entity Linking," CoNLL 2018) built the first neural end-to-end EL system that jointly discovers and links entities, but reported that it "significantly outperforms popular systems on the Gerbil platform *when enough training data is available*" — you do not have that data (≈1,451 links, of which only a fraction are clean Tier-A). Staged pipelines (BLINK: bi-encoder retrieval → cross-encoder rerank) are simpler, more debuggable, and the dominant production pattern. Adopt staged.

2. **Your corpus is tiny (258 notes / 3,184 units), which flips several standard recommendations.** ColBERT/PLAID late interaction exists to make token-level matching *scale to millions of passages* (PLAID is benchmarked at 140M passages); at 258 targets that scaling machinery is pure overhead. Multi-vector MaxSim is still useful — but as a *reranking feature and boundary-localization signal*, not as your retrieval index. A brute-force exact search over ~3k unit vectors is instantaneous; you need no ANN index at all.

3. **Existing links are weak supervision, not gold.** The deployed Wikimedia add-a-link model deliberately restricts its gold set to the *first linked sentence* of an article to avoid false negatives, filters anchors by link-probability > 6.5% (Milne & Witten keyphraseness), and the classic Milne & Witten "Learning to Link with Wikipedia" (CIKM 2008) detector/disambiguator reaches "recall and precision of almost 75%." Your Tier-C (Related-notes/index/heading/table) links are good *graph edges* but *bad anchor-placement examples* and must be separated, exactly as your tiering proposes.

4. **Unlinked spans are NOT safe negatives.** This is a textbook positive-unlabeled (PU) problem: an unlinked "MapReduce" is very often a true-but-unauthored link, not a negative. RocketQA's central finding — that mined hard negatives contain false negatives (unlabeled positives) that *hurt* bi-encoder training unless denoised with a cross-encoder — is the retrieval-side version of the same hazard. Use PU-style class weighting and denoised/confirmed negatives.

5. **Calibration is a solved, cheap problem and is the lever that makes your no-link threshold correspond to a predictable human acceptance rate.** Guo, Pleiss, Sun & Weinberger ("On Calibration of Modern Neural Networks," ICML 2017) show that "temperature scaling — a single-parameter variant of Platt Scaling — is surprisingly effective at calibrating predictions"; the parameter T is "chosen to optimize the model's likelihood on a held-out portion of the training data" and notably "does not change the most-confident prediction." Conformal prediction with a reject option (Linusson et al.) gives distribution-free guarantees on the error rate among *accepted* suggestions — precisely the "score threshold → predictable acceptance rate" property you want.

6. **Useful links are rare and compete for attention.** Paranjape, West, Zia & Leskovec ("Improving Website Hyperlink Structure Using Server Logs," WSDM 2016) found that "in the English Wikipedia, of all the 800,000 links added...in February 2015, the majority (66%) were not clicked even a single time in March 2015...only 1% of links added in February were used more than 100 times in all of March," and that "simply adding more links does not increase the overall number of clicks taken from a page. Instead, links compete with each other for user attention." This is the empirical mandate for your sparse global selection and per-note link budget.

## Details

### 1. Preferred problem formulation (Deliverable 1)

**Recommendation: closed-world *span detection + entity linking* with a rejection option, staged into 4–5 modules, with span-to-document as the v1 target granularity and span-to-section added only for placement.**

- **Not relation extraction.** RE presupposes a typed relation schema and treats link-placement as a byproduct; your links are untyped "see also / this concept lives there" navigation edges. RE adds schema burden with no payoff. Keep a relation-extraction framing out of scope.
- **Mention detection + closed-world EL is the correct core** (Question 1). The closed world is your 258-note catalog. This mirrors BLINK's zero-shot EL, in which "each entity is defined only by a short textual description" (here, note title + summary + headings) and the Wikimedia add-a-link task (literally "given source text, propose anchor + target-page from the wiki's own catalog").
- **Span-to-document is sufficient for v1 (Question 3).** Add span-to-section (span-to-span) alignment only in Stage 3 when you need to justify *where* in a long target the concept lives, or when a note's useful concept is spread across sections (Question 4). Represent such a target as a **hierarchical document/section entity** (Question 5): a single document-level vector for retrieval + a small set of section-level vectors for reranking/placement. This is the multi-granularity view DensePhrases validated — a single retriever serving phrase/sentence/passage/document granularity via a max over constituent scores.
- **Train span detection and target linking separately (Question 2):** high-recall Markdown-aware span proposal first (deterministic + light classifier), then linking trained separately on audited positives. Joint training is not justified at your data scale.

### 2. Candidate architectures, ranked by quality/cost (Deliverable 2)

**Architecture A — Frozen-encoder heads (RECOMMENDED for v1).** Keep Qwen3-Embedding-0.6B frozen. Train only: (i) a small MLP "naturalness/linkability" span scorer on top of pooled span representations + hand features; (ii) reuse the frozen bi-encoder for target retrieval; (iii) a small cross-encoder-style reranker head (or a lightweight fine-tuned cross-encoder) over (span-context, target-description) pairs.
- *Quality:* high relative to data available; least overfitting risk. In the low-data regime (<1,000 examples) frozen heads and LoRA reliably beat full fine-tuning, which overfits.
- *Cost:* lowest. Trains in minutes on MPS; no encoder gradients. **This is the "frozen-encoder baseline" immediate experiment and should also be your v1.**

**Architecture B — LoRA/adapter fine-tune of the encoder + heads (upgrade path).** If frozen heads plateau below your quality bar and the audit yields ≥ a few hundred clean Tier-A positives, add LoRA adapters (rank 4–8) to the encoder. The RepLLaMA retrieval result found LoRA generalizes *better* than full fine-tune on independent human judgments (full FT overfit the training distribution) — directly relevant since your gold is noisy. (Note the countervailing "intruder dimensions" finding that LoRA can forget across sequential tasks — not a concern for a single-task adapter.)
- *Quality:* modest expected gain, mostly on target retrieval recall.
- *Cost:* moderate; still MPS-feasible at 0.6B with rank-4 adapters and small batch.

**Architecture C — Full fine-tune / autoregressive generative linker (GENRE-style) (NOT recommended now).** GENRE generates the target title token-by-token with a constrained trie ("constrained beam search") over valid titles — elegant for a closed catalog and worth noting as prior art — but it needs far more supervision than you have and is the most overfit-prone. Full fine-tuning of a 0.6B model on ~1k noisy labels will memorize. Defer.

**Ranking:** A > B ≫ C for your setting. Ship A; keep B as a measured upgrade gated on the audit.

### 3. Component design decisions (Questions 6–11)

- **ColBERT multi-vector is overkill as an index at 258 docs (Question 7).** Use a bi-encoder for retrieval + a cross-encoder reranker (the BLINK pattern, which the authors show is state of the art "despite its relative simplicity (e.g. no explicit entity embeddings or manually engineered mention tables)"). Reserve token-level MaxSim as a *reranker feature and for boundary localization* (Question 8), not as the retrieval mechanism.
- **Smith-Waterman-style local alignment (Question 9):** implement only as an optional bounded-band reranking feature, not a core stage. After a learned cross-encoder, expect it to add complexity with marginal quality gain; make it an ablatable feature and drop it if it doesn't move validation precision.
- **Span representation (Question 10):** the coreference literature (Lee et al. 2017 e2e-coref; SpanBERT) converged on `[start_token, end_token, attention-pooled interior, width/features]`. Use exactly this: concatenate the start and end token states, an attention- or mean-pooled interior vector, plus your hand features. SpanBERT's design rationale — endpoints capture context, the interior/head attention vector "best represent[s] the internal span itself" — tells you not to drop either. Do **not** separately re-encode each candidate span through the full model (too expensive on MPS and unnecessary).
- **Technical identifiers / code / Markdown (Question 11):** handle with region masks from the Markdown parser (exclude code fences, tables, math, YAML frontmatter) *plus* a whitelist/keyphraseness signal so legitimate terms like IPv4, MapReduce, head-of-line blocking survive. The anchor-dictionary keyphraseness statistic (fraction of times a string appears *as* a link) is the principled filter Wikimedia uses (threshold 6.5%, "similar to filtering stopwords in NLP"); compute the analogue over your own corpus.

### 4. Minimum data audit before any training (Deliverable 3; Questions 12–14)

**This is the first thing to build, before any model.** If the audit shows existing links are too noisy for even weak supervision, the first deliverable becomes the annotation tool + expert benchmark, not a trained linker — this is a real branch you should be prepared to take.

- **Sample size:** label a **stratified sample of 150 existing links** (your suggested number is well-judged). Stratify by: region type (prose / Related-notes / heading / table / code / citation), anchor length (1 word / 2–3 / 4+), target area (topic family), and source doc type. 150 is enough to estimate a proportion to roughly ±8% at 95% confidence and to populate each stratum; go to 200–300 if strata are too thin.
- **Label schema:** for each link record (a) target correctness, (b) anchor naturalness, (c) region type, (d) placement validity, mapping to your A/B/C/D tiers.
- **Agreement:** use **two annotators on an overlapping subset and report Cohen's κ** (two raters, nominal) or **Krippendorff's α** (handles >2 raters / missing data / ordinal). Interpret on the Landis–Koch scale: 0.61–0.80 = substantial, ≥0.81 = almost perfect (Artstein & Poesio note 0.8 as a common working threshold). Target κ ≥ 0.6 before trusting the labels; if κ < 0.4 on "naturalness," your definition is underspecified — refine the guideline and re-label.
- **Tiering rules (Question 14):** Tier A = strong positives for *all* heads. Tier B = weak positives / review-only (downweight, use for target-correctness but not anchor-naturalness). Tier C = **graph supervision only** — use as target-retrieval positives but **exclude from the span/naturalness head** (Related-notes lists are correct edges but terrible anchor examples). Tier D = exclude or use as negatives. Do **not** delete Tier C globally; it is signal for retrieval and noise for placement — model them separately.

### 5. Best use of existing links as weak supervision (Deliverable 4; Questions 15–20)

- **Weak supervision from note metadata (Question 19):** titles, descriptions, headings, and aliases give you a strong, *clean* signal that needs no external corpus. This is exactly the Wikimedia anchor-dictionary approach: build a `{mention → {target: count}}` dictionary from your own resolved links plus title/alias matches, with the same preprocessing (normalize/lowercase anchors, resolve redirects/aliases, keep only main-namespace targets). This alone bootstraps candidate generation and the commonness prior.
- **Hard negatives (Question 15):** construct from (i) similar-but-unlinked notes (nearest neighbors in embedding space), (ii) sibling target titles in the same topic family, (iii) *alternative* targets for a genuinely ambiguous anchor (the Wikimedia "Berlin → Berlin, Wisconsin / Berlin the band" pattern), (iv) same-anchor-different-target pairs. Mine with the frozen bi-encoder (ANCE-style asynchronous mining), then **denoise with the cross-encoder** (RocketQA) to strip false negatives before they poison training.
- **Unlinked spans and PU learning (Question 16):** treat unlinked candidate spans as *unlabeled, not negative*. Options in increasing sophistication: (a) class-prior weighting — weight pseudo-negatives by an estimated link prior π (biased/cost-sensitive PU, the common "assign small weights to unlabeled-as-negative" approach); (b) confirmed negatives only — a span is negative only if its top retrieved target is confidently unrelated (cross-encoder score below a low threshold); (c) self-training with a curriculum (start with "easy" confident negatives via a hardness measure, add harder ones over epochs, per the noise-self-correction PU line). Start with (a)+(b).
- **Wikipedia (Questions 17–18):** **pretrain the mention/keyphraseness head on Wikipedia anchors, then adapt; skip Wikipedia for the target linker.** Wikipedia's anchor statistics transfer well to "what strings are linkable in prose" (keyphraseness is domain-general — it is the basis of Mihalcea & Csomai's Wikify! and Milne & Witten), but its *entities* are not your notes, so there is no clean mapping for the target side (Question 18 has no good answer — don't force one). Run this as the "Wikipedia transfer ablation" experiment and keep it only if it beats in-domain-only on your benchmark.
- **Leakage control (Question 20):** a repeated anchor phrase ("gradient descent") or a popular target appearing in both train and test lets the model memorize. Split by **document** *and* by **anchor-string** *and* by **target** so no anchor or target straddles the split.

### 6. Losses, calibration, and starting hyperparameters (Questions 21–26)

- **Span/naturalness head (Question 21):** frame as **span classification with a listwise ranking auxiliary**, not BIO tagging (BIO forces a single segmentation; you want to score overlapping candidates independently and let global selection choose). Binary cross-entropy per candidate span + a listwise loss (softmax over candidate spans in a sentence) to calibrate relative naturalness. This mirrors the e2e-coref unary mention score followed by pruning.
- **Target retrieval (Question 22):** **contrastive InfoNCE with in-batch + mined hard negatives** (DPR/ANCE standard). Sampled softmax is fine at 258 targets — you can normalize over the *entire* catalog every step, which removes the in-batch-negative approximation entirely. This is a rare case where full-catalog softmax is cheap; use it.
- **Reranker (Stage 3):** cross-encoder trained with pairwise/listwise ranking over the retrieved candidate set, with hard negatives from Stage 2 (monoBERT/monoT5-style scoring of the concatenated span-context + target text).
- **No-link decision (Question 23):** train a dedicated rejection head with clearly-unrelated span-target pairs as negatives (your "no-link calibration" experiment). At inference, abstain when the calibrated top-target probability is below threshold τ — the selective-prediction / Chow's-rule reject option.
- **Separate vs collapsed scores (Questions 24–25):** keep **three explicitly separate heads — anchor naturalness, target correctness, source-placement validity** — and combine them at global selection, rather than one collapsed score. This is what lets you handle the target-correct-but-anchor-wrong case (Question 25): high target-correctness × low anchor-naturalness → surface as a *review suggestion with a proposed better anchor*, not an auto-link. A collapsed score cannot express this.
- **Calibration (Question 26):** fit **temperature scaling** on a held-out validation set (single parameter T, minimize NLL). Because T "does not change the most-confident prediction," it re-shapes probabilities without reordering — ideal for turning a raw score into a meaningful accept probability. For a *guaranteed* acceptance rate use **conformal prediction with a reject option**, which lets you set "at most k errors among accepted suggestions" without revealing test labels. Temperature scaling is known to degrade on very small or noisy validation sets, so reserve ≥100–150 clean judgments for calibration and prefer conformal if that set is small.

### 7. Evaluation suite and quality bar (Deliverable 8; Questions 27–32)

- **Build a small expert-labeled benchmark (Question 29), untouched during development.** It should include, per your list: a natural linkable span; an acceptable-but-non-ideal span; a correct target; an incorrect target; a should-not-link case; a valid source location; and a valid reverse-direction anchor. Over-sample hard cases: semantically related notes with different vocabulary, code-heavy notes, index notes, generic anchors, and heavily-linked notes.
- **Primary metric (Question 27): end-to-end accepted-link precision@1 on reviewed proposals**, reported at a fixed recall operating point, plus target Recall@k and MRR as retrieval diagnostics, plus source-span F1 for the detection stage. Human preference on a sample is the tiebreaker. Precision-oriented, because a review tool's cost is false positives.
- **Noisy/missing labels (Question 28):** use **judged-only metrics and pooling** (TREC-style): pool the top-k suggestions from each system variant, have a human judge that pool, and compute precision over judged items; treat unjudged as unknown (report a residual, or use bpref-style measures that are robust to incomplete judgments) rather than silently scoring them non-relevant, which — as the IR pooling-bias literature shows — biases against new systems that surface un-pooled-but-correct links.
- **Quality bar (Question 30):** **precision@1 ≈ 0.75–0.80 at ~40% recall for v1.** This mirrors the deployed Wikimedia add-a-link deploy gate: per Gerlach et al. (CIKM 2021), "In practice, we required a precision of 0.7-0.75 or higher such that the majority of suggestions would be true positives. As a result, we discarded models for 23 languages," and their backtesting showed that "for all languages, we can find a setting in which one can obtain a precision ≥ 80% while at the same time keeping recall above 40%." Explicitly reject historical-link *recovery* as the target (most historical links are unused). Raising the accept threshold toward precision ~0.90 will roughly halve recall — acceptable for a review tool.
- **Links per note (Question 31):** enforce a **per-note budget** (start ~1 suggestion per 150–200 words, capped) — the WSDM 2016 result shows clicks-per-page saturate and links compete for attention; densely annotating a note is actively harmful. Their prescription: "spread high-clickthrough links across many different source pages" rather than piling them onto one.
- **Navigation value (Question 32):** the honest long-term metric is whether suggested links get *used/accepted*, not whether they match historical author behavior. Instrument acceptance rate in the review tool as your real-world signal; if you ever have revision/access history, a click/traversal proxy is the gold standard (this is exactly why West/Leskovec used server logs and navigation traces instead of the existing link graph).

### 8. Validation and split design

- **No random row splits.** Use **document-held-out** as primary; add **topic/section-family-held-out** to test generalization to new subject areas; add a **temporal split** if you have revision history; and keep the **hand-labeled test set frozen**.
- Split additionally by anchor-string and target to prevent lexical leakage (§5, Question 20).
- Report metrics per split; a large gap between random and document-held-out performance is your leakage alarm.

### 9. Optimization for small-corpus local MPS hardware

- **No ANN index.** 258 doc vectors and ~3,184 unit vectors fit in memory; exact dot-product search is sub-millisecond. Skip FAISS/PLAID entirely. (PLAID/ColBERT exist for ~140M-passage scale — irrelevant here.)
- **Precompute and cache** all target embeddings once (they change only when notes change); recompute incrementally per edited note.
- **Frozen encoder = no backprop through 0.6B params;** only tiny heads train. This is the single biggest MPS win. Qwen3-Embedding-0.6B is a decoder-style model using **last-token pooling with causal masking**, so for token-level/span features be aware that pooled unit vectors already aggregate left-context; extract token states explicitly (as your preflight did for 64 units) rather than assuming BERT-style bidirectional token vectors. Qwen3 supports **MRL (custom output dimensions)** and is **instruction-aware** — keep your 1,024-dim pin, and use task instructions (Qwen reports instructions "typically yield an improvement of 1% to 5%") written in English, per the model card's own guidance.
- **Batch cross-encoder reranking** over the small candidate set; cap candidates per span (e.g., top-10 targets) to bound compute. Cross-encoder inference is the runtime cost; at your scale it is still trivial, but the per-span target cap keeps it linear.

### 10. Threshold / budget / calibration tuning guidance

- **Accept threshold τ:** tune on the validation set to hit your target precision (start where precision ≈ 0.78). Expect the Wikimedia-shaped tradeoff: moving τ from the 0.5-equivalent to the 0.8-equivalent raised precision from ~0.75–0.81 to ~0.89–0.92 while recall roughly halved.
- **Keyphraseness floor:** start at the Milne–Witten-style **link-probability > ~6.5%** for anchor eligibility; tune on your corpus.
- **Per-note link budget:** start at 1 per 150–200 words, hard-cap (e.g., ≤ 8–10 per note); tune down if reviewers report density fatigue.
- **Calibration temperature T:** fit by NLL on held-out validation; a single scalar. Re-fit whenever the encoder or heads change.
- **Negative sampling ratio:** start at **1 positive : 4–8 negatives** for the retrieval/reranker heads (DPR-era default), with hard negatives a minority (e.g., 1–2 hard + rest in-batch) to avoid the RocketQA false-negative trap; denoise hard negatives with the cross-encoder before use.
- **MMR diversity (global selection):** the Carbonell & Goldstein MMR score is `λ·Rel(item) − (1−λ)·max Sim(item, selected)`. Use λ ≈ 0.5–0.7 (relevance-leaning) for a precision-oriented review tool; lower λ toward 0.3 only if reviewers want more exploratory/diverse suggestions. Also apply target-redundancy penalties so the same target isn't suggested from many near-duplicate spans.

### 11. Phased build plan (Deliverable 6 — first experiment changes nothing in production)

1. **Audit (no pipeline change):** build the annotation tool; label 150 stratified links; compute κ/α; decide go/no-go on weak supervision. *Kill/branch point.*
2. **Candidate recall check:** verify the high-recall span generator actually contains the audited positive anchors (recall ceiling). If it misses them, fix generation before modeling.
3. **Frozen-encoder baseline (Architecture A):** train span + retrieval + rerank heads on the exported pooled/token vectors — **entirely offline, no production change.**
4. **Reranker bake-off:** compare lexical vs pooled-vector vs MaxSim vs cross-encoder rerankers on identical candidate sets.
5. **No-link calibration:** inject clearly-unrelated pairs; measure false-link rate vs threshold; fit temperature / conformal.
6. **Document-held-out + anchor/target split** evaluation on the frozen benchmark.
7. **Wikipedia transfer ablation:** in-domain-only vs Wikipedia-keyphraseness-pretrained + in-domain. Keep only if it wins.
8. Only then consider **Architecture B (LoRA)** as a measured upgrade.

### 12. Failure modes and kill criteria (Deliverable 7)

- **Audit failure:** if inter-rater κ on "naturalness" stays < 0.4 after guideline refinement, the target concept is ill-defined — *stop and re-scope the annotation task* rather than training on incoherent labels.
- **Candidate-generation ceiling:** if the high-recall generator's recall of audited positive anchors is < ~85%, no downstream model can recover — fix generation first.
- **PU collapse:** if treating unlinked spans as negatives makes the model predict "no-link" almost everywhere (precision high, recall ~0), that's the false-negative trap — switch to PU weighting / confirmed-negatives.
- **KILL CRITERION for the learned approach:** if, after the frozen-encoder baseline + reranker + calibration, **end-to-end precision@1 on the frozen expert benchmark cannot reach ~0.70 at any usable recall (say ≥ 20%)**, the learned linker is not ready to ship. Fall back to the deterministic keyphraseness + anchor-dictionary + bi-encoder baseline (essentially the Wikimedia XGBoost feature model: ngram length, anchor-target frequency, ambiguity, Levenshtein, embedding similarity) as the review-tool engine, and revisit only with more labeled data.
- **Over-linking:** if reviewers reject primarily because notes become too dense, the budget/MMR is mis-tuned, not the model — tighten the budget before retraining.

## Recommendations

**Do now (Phase 1–3, no production change):**
1. Build the annotation tool and audit 150 stratified links; report Cohen's κ / Krippendorff's α and the A/B/C/D tier distribution. This gates everything.
2. Build the self-corpus anchor dictionary (`mention → {target: count}`) and keyphraseness statistic; set the eligibility floor near 6.5% and tune.
3. Train Architecture A (frozen Qwen3 + three small heads: naturalness, target-retrieval via full-catalog softmax, cross-encoder rerank) on audited Tier-A/B positives, with PU-weighted/denoised negatives.
4. Stand up the frozen expert benchmark with the seven judgment types and hard-case oversampling; never train on it.

**Decision thresholds that change the plan:**
- κ ≥ 0.6 and ≥ ~150 clean Tier-A positives → proceed to modeling; κ < 0.4 → re-scope annotation.
- Architecture A reaches precision@1 ≥ 0.75 at ≥ 40% recall → ship as review tool.
- A plateaus in 0.60–0.75 → try Architecture B (LoRA rank 4–8) and the Wikipedia keyphraseness ablation.
- A cannot exceed 0.70 at ≥ 20% recall → invoke kill criterion; ship deterministic baseline instead.

**Operating points:** default accept threshold at precision ≈ 0.78; per-note budget ~1 link / 150–200 words capped at ≤10; MMR λ ≈ 0.6; negative ratio 1:4–8 with denoised hard negatives; temperature scaling (or conformal reject option) fit on ≥100 held-out clean judgments.

## Caveats

- **The literature is thin for your exact setting** (a ~250-document personal closed-world corpus). Entity-linking and dense-retrieval results are from web/Wikipedia scale; I have flagged where scale inverts the standard advice (no ANN, full-catalog softmax, frozen-over-fine-tuned, multi-vector-as-feature-not-index). These small-scale inversions are **judgment calls reasoned from first principles**, not established benchmarks.
- **Well-established** (high confidence): the BLINK bi-encoder→cross-encoder staging; SpanBERT/Lee-style span representations; temperature scaling (Guo et al. 2017); MMR (Carbonell & Goldstein 1998); PU-learning hazards and RocketQA denoising; the Wikimedia add-a-link precision/recall envelope and Milne & Witten's ~75% precision baseline; West/Leskovec's link-usefulness and budget findings.
- **Judgment calls** (medium confidence): the exact 0.75–0.80 precision bar (borrowed from a Wikipedia-scale deployment; your private corpus may behave differently), the 150-sample audit size, the specific hyperparameter starting points, and whether Wikipedia keyphraseness transfer will actually help on a technical-notes domain (must be measured).
- **Metric non-comparability:** the Wikimedia precision/recall and the West/Leskovec precision@k are measured differently and against different notions of "correct." Use them as envelope guidance, not directly transferable targets.
- **Deployed add-a-link production acceptance** is reported publicly as a rejection rate below its 30% threshold rather than a single exact acceptance percentage; treat "< 30% rejection" as a corroborating datapoint consistent with ~75–80% backtesting precision.
- The system should **preserve Markdown correctness and never overlap existing links** — enforce this as a hard post-processing constraint outside the learned scores, exactly as Wikimedia layers hard-coded (non-)linking rules on top of its classifier.
