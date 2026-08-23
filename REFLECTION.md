# Reflection

**The hardest part** was the "never invent a number" requirement — not because
checking numbers is hard, but because deciding *where to put the check* is an
architecture question. Prompting the model to be honest is not engineering;
putting an LLM critic in charge is circular (an LLM policing an LLM). The design
I landed on is layered: a deterministic verifier that extracts every figure from
the draft and refuses anything that doesn't trace to recorded tool output
(immune to persuasion, costs zero tokens), *then* a small-model critic for the
semantic failures regexes can't see — a "42.7%" that traces fine but is quoted
for the wrong segment, or a "higher" that should be "lower". Getting the
deterministic layer to be strict without being unusable (percent vs fraction
forms, rounding, list markers, years) took the most iteration, and my own test
suite caught three real bugs in it.

**What I learned / had to teach myself:** how far you can get with an
in-process AST-validated sandbox before you need real isolation (further than I
expected, but I now know exactly where the line is — my tests attack it with
`__mro__` chains and pandas I/O escapes); and that free-tier rate limits are a
genuine design input, not an annoyance — the cache/routing/backoff decisions all
fell out of treating 429s as part of the spec. One humbling find: a runaway
sandbox thread kept the whole test process alive for nine minutes, which taught
me more about Python thread lifecycle than any tutorial has.

**What I'd do differently with more time:** run the eval set `--live` across
several planner models and publish the comparison (the harness is ready; I built
ground truths first precisely so this is a one-command experiment); replace the
baseline-substitution attributions with SHAP values behind the same interface;
move the sandbox into a subprocess with rlimits for true isolation; and add a
conversation-level eval (the multi-turn memory is tested, but not *measured*).
I'd also calibrate the model's probabilities (isotonic) — "risk 0.66" should
mean 66% empirically, and right now that claim is only approximately true.
