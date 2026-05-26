# RAPTOR — Medium Series

An 8-post series breaking down modern AI-augmented security analysis, built around the open-source [RAPTOR](https://github.com/grokjc/raptor) framework. Each post is a standalone Medium-length read (~6–10 minutes); together they build from "what is SAST?" to "how does multi-model LLM orchestration validate exploit feasibility?"

## At a glance

- **Format:** 8 posts, each readable standalone, designed for technical blog platforms.
- **Progression:** foundations first (Posts 1–4), framework integration next (Posts 5–8).
- **Audience:** security practitioners and AI/ML engineers building real systems.

**Editorial structure.** The first four posts are pure educational content on security techniques (pattern matching, dataflow, SMT, fuzzing) — no product pitch, no framework name-checking. RAPTOR enters the picture in Post 5 as one specific way of wiring all of this together. Posts 6–8 zoom into the framework's distinctive parts (binary exploit feasibility, the LLM validation pipeline, the full agentic workflow). Post 8 ends with a candid limitations section.

The series is written for two overlapping audiences:

- **Security engineers and red teamers** new to AI-augmented tooling, curious about what changes when an LLM is treated as a first-class component
- **AI/ML engineers** curious about applied LLM systems — each post includes a dedicated section on engineering patterns that generalize beyond security

Early posts are beginner-friendly (vocabulary primer, conceptual introductions). Depth ramps up across the series. By Post 6 we're walking through ROP gadget feasibility and libc fingerprinting; by Post 7 we're talking about stage-decomposed LLM pipelines and fresh-context verification.

## Reading order

1. **[Introduction to AI-Native Security Research](./01-introduction-ai-native-security.md)** — What "AI-native" means in practice, the four scanning pillars at a conceptual level, and a vocabulary primer for SAST / DAST / SCA / fuzzing / CWE / CVE / CVSS / SARIF. *Tool-agnostic.*

2. **[Pattern Matching at Scale](./02-semgrep-pattern-matching.md)** — Why pattern matchers exist (grep is too imprecise, hand-written AST visitors too expensive), the categories where pattern matching dominates, and where it stops being useful. *Tool-agnostic with Semgrep as running example.*

3. **[Dataflow Analysis](./03-codeql-dataflow-analysis.md)** — Why pattern matching has fundamental limits, the source/sink/sanitizer model, and how taint tracking finds bugs that span multiple functions. *Tool-agnostic with CodeQL as running example.*

4. **[SMT Solvers and Killing False Positives](./04-z3-smt-solver-filtering.md)** — SMT from first principles, bitvector arithmetic for C semantics, and a walk through eight worked cases showing SAT, UNSAT, and indeterminate paths. *Tool-agnostic with Z3 as running example.*

5. **[Fuzzing, and Where RAPTOR Enters](./05-afl-coverage-guided-fuzzing.md)** — Why static analysis can never substitute for actually running the code, how coverage-guided mutation works, and the first introduction in the series to the RAPTOR framework that wires all of this together.

6. **[Binary Exploit Feasibility](./06-binary-exploit-feasibility.md)** — The evolutionary arms race between mitigations (NX, ASLR, PIE, RELRO, canaries, CET) and attack techniques (ROP, info-leaks, one-gadgets). What separates "the program crashed" from "the program is exploitable."

7. **[The LLM Validation Pipeline](./07-llm-validation-pipeline.md)** — Eight stages of structured skepticism. Leads with **the fresh-context verifier pattern** — the single most generalizable AI-architectural idea in the series. If you read only one post, read this one.

8. **[Putting It All Together — Honestly](./08-agentic-workflow-and-examples.md)** — Full pipeline walked through with real Python, JavaScript, and C examples. Ends with a substantial limitations section covering build-system fragility, stateful fuzzing gaps, LLM hallucination, multi-model cost, alpha/beta features, and the false-negative problem.

## What's not in the series

These topics are deliberately out of scope; they're worth their own posts if there's interest:

- **SCA deep dive** — typosquat detection methodology, dependency graph traversal, version constraint resolution
- **Web scanning architecture** — crawler design, parameter mutation strategies, ffuf integration
- **Multi-model consensus statistics** — empirical reliability data from RAPTOR's scorecard system
- **Real-world case studies** — applying the full pipeline to specific open-source projects

## Source material

This series is a structured rewrite of [`docs/raptor-scanning-deep-dive.md`](../raptor-scanning-deep-dive.md), which remains in the repository as the single-document reference. The series adds beginner-friendly framing, the explicit *why this technique exists* angle, AI/ML engineering perspective, fresh-context verification as a featured architectural pattern, a candid limitations section, and 2–4 external citations per post.
# help-contribute
