# Glossary — Attention Is All You Need

## Auto-regressive
Generating a sequence one element at a time while feeding the model's own previous outputs back in as inputs: "consuming the previously generated symbols as additional input when generating the next" (§3, p.2). Same idea as an AR time-series model — past values of the outcome enter as covariates for the next value — except here the "past values" are the words the decoder has already emitted.
**Link**: [Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* — autoregressive models](https://otexts.com/fpp3/AR.html)
*Tags*: sequence-modeling, decoding · *first needed*: §3

## Multi-head attention
Running several attention functions ("heads") in parallel — here h = 8 — each on its own learned low-dimensional projection of the queries, keys, and values, then concatenating and re-projecting the outputs. Lets the model "jointly attend to information from different representation subspaces at different positions," which a single averaged head inhibits (§3.2.2, p.5). Like fitting several small smoothers on different learned covariate projections and combining them, rather than one smoother on everything.
**Link**: [Dive into Deep Learning — multi-head attention](https://d2l.ai/chapter_attention-mechanisms-and-transformers/multihead-attention.html)
*Tags*: attention, architecture · *first needed*: §3.2.2

## Query, key, value (Q, K, V)
The three vector roles in an attention function: the query is the position asking for information; each candidate position offers a key (used to score how relevant it is to the query) and a value (the content that gets averaged). The output is a weighted sum of values, weights from query–key compatibility (§3.2, p.3–4). Think of predicting for a new observation by averaging outcomes (values) of past observations, weighted by how similar their profiles (keys) are to the new one's profile (query).
**Link**: [Dive into Deep Learning — queries, keys, and values](https://d2l.ai/chapter_attention-mechanisms-and-transformers/queries-keys-values.html)
*Tags*: attention · *first needed*: §3.2

## Scaled dot-product attention
This paper's attention function: score each query against all keys by dot product, divide by √d_k, softmax the scores into weights, and take the weighted sum of values — Attention(Q, K, V) = softmax(QKᵀ/√d_k)V (§3.2.1, p.4, eq. 1). The √d_k divisor standardizes the scores so large key dimensions do not saturate the softmax.
**Link**: [Vaswani et al. 2017, arXiv:1706.03762 — the term's original paper](https://arxiv.org/abs/1706.03762)
*Tags*: attention, equations · *first needed*: §3.2.1

## Self-attention
"an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence" (§2, p.2) — the sequence attends to itself: every position builds its representation as a weighted average over (projections of) all positions of the same sequence, rather than over a separate input sequence.
**Link**: [Dive into Deep Learning — self-attention](https://d2l.ai/chapter_attention-mechanisms-and-transformers/self-attention-and-positional-encoding.html)
*Tags*: attention · *first needed*: §3

## Softmax
The function that turns a vector of real-valued scores into positive weights summing to 1: exponentiate each score, divide by the sum of exponentials. You know it as the link function of multinomial logistic regression, turning linear predictors into class probabilities; here it turns scaled query–key scores into the weights on the values (§3.2.1, p.4).
**Link**: [Goodfellow, Bengio & Courville, *Deep Learning*, §6.2.2 — softmax units](https://www.deeplearningbook.org/contents/mlp.html)
*Tags*: functions · *first needed*: §3.2.1
