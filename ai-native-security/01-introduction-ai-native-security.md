# What Does "AI-Native Security Research" Actually Mean?

> Part 1 of an 8-post series. Start here if you're new to security tooling, AI-augmented analysis, or both. The first four posts are pure groundwork — no product pitch, just the techniques and the reasons they exist. Later posts get specific.

---

I want to start with an image you probably recognise. You're walking the floor at a security conference — RSA, Black Hat, it doesn't matter — and every third booth has a banner screaming "AI-powered security." The demo always looks roughly the same: a scanner runs, a wall of alerts appears, and then the chatbot summarises them. Sometimes well. Sometimes not. And at the end of it, you're still left staring at the exact same question every security engineer has wrestled with for twenty years: *which of these findings is actually real?*

That's the itch this series is trying to scratch.

Because here's the thing — the interesting question isn't whether you can bolt a language model onto the front of a scanner. The interesting question is: what changes when you design the *entire pipeline* assuming the LLM is a first-class component? Not the UI. Not the rephraser. The actual reasoning layer that decides what to investigate, how deeply, and when to stop.

That shift in framing is what I want to explore across these eight posts. We'll cover static analysis, dataflow tracing, constraint solving, coverage-guided fuzzing, binary exploit feasibility, and multi-model LLM orchestration — and for each one, we'll ask *why it exists* before we look at how it works.

If you've never written a Semgrep rule or run a fuzzer, this first post is your vocabulary primer. If you have, skim the glossary and meet me at the four pillars.

---

## Series navigation

- **📌 Understanding AI-Native Security (Part 1): What this all actually means — and a vocabulary primer (this blog post!)**
- Understanding AI-Native Security (Part 2): Pattern Matching at Scale — Why a regex isn't enough (coming soon!)
- Understanding AI-Native Security (Part 3): Dataflow Analysis — When pattern matching isn't enough (coming soon!)
- Understanding AI-Native Security (Part 4): SMT Solvers and the Math of Killing False Positives (coming soon!)
- Understanding AI-Native Security (Part 5): Fuzzing, and Where RAPTOR Enters the Story (coming soon!)
- Understanding AI-Native Security (Part 6): Binary Exploit Feasibility — From crash to constraints (coming soon!)
- Understanding AI-Native Security (Part 7): The LLM Validation Pipeline (coming soon!)
- Understanding AI-Native Security (Part 8): Putting It All Together — Honestly (coming soon!)

---

## In this post

- A vocabulary primer for the acronyms you'll see everywhere: SAST, DAST, SCA, Fuzzing, CWE, CVE, CVSS, SARIF, and taint analysis
- The four pillars of modern attack surface coverage — and why you need all four
- Where AI assistance actually helps in a security pipeline, and where it predictably fails
- The architectural pattern that fixes most AI security failures (spoiler: it's about stage decomposition)
- A preview of everything the rest of the series covers

---

## A vocabulary primer (skip if you live in this world)

Security tooling has accumulated more acronyms than any field deserves. Don't worry — I'll keep this tight. Here are the ones you need to follow everything else in the series.

**SAST** — *Static Application Security Testing.* Tools that analyse source code without running it. They read your files, build some model of what the code does, and look for patterns or paths that match known vulnerability shapes. *Why it exists:* because reading every line of every PR by hand doesn't scale, and the most common vulnerability shapes are mechanically detectable.

**DAST** — *Dynamic Application Security Testing.* Tools that interact with a running application. They hit your endpoints, send malformed inputs, watch for crashes or unexpected responses. *Why it exists:* because some bugs only appear at runtime — configuration mistakes, environment-dependent behaviour, race conditions — and source code can't tell you they're there.

**SCA** — *Software Composition Analysis.* Tools that look at your dependencies (`package.json`, `requirements.txt`, `Cargo.toml`) and cross-reference them against vulnerability databases. *Why it exists:* because most application code is dependencies, and you can't audit code you didn't write at the rate dependencies are updated.

**Fuzzing** — A specific kind of dynamic testing where you generate enormous volumes of random or semi-random inputs and watch for crashes. Modern *coverage-guided* fuzzers do this intelligently: they keep mutating inputs that exercise new code paths, and discard ones that don't. *Why it exists:* because static analysis can argue a bug *might* exist; only a fuzzer can hand you the exact 47 bytes that crash the program.

**CWE** — *[Common Weakness Enumeration](https://cwe.mitre.org/).* A community-maintained dictionary of vulnerability *types*. CWE-89 is "SQL injection." CWE-79 is "Cross-site scripting." CWE-120 is "Classic buffer overflow." When tools tag findings, they use CWE IDs. *Why it exists:* so two different tools talking about "the same kind of bug" actually mean the same thing.

**CVE** — *[Common Vulnerabilities and Exposures](https://cve.mitre.org/).* A specific, publicly-disclosed vulnerability in a specific product, with a unique ID like `CVE-2024-3094`. CVEs are *instances*; CWEs are *categories*. Think of CWE as the species and CVE as the individual organism.

**CVSS** — *[Common Vulnerability Scoring System](https://www.first.org/cvss/v3.1/specification-document).* A formal vector for scoring how bad a vulnerability is. The version most tools emit (3.1) decomposes severity into attack vector, complexity, required privileges, user interaction, scope, and impact on confidentiality/integrity/availability. CVSS gives you the familiar 0.0–10.0 score, but the *score* is downstream of the *vector*. *Why it exists:* because "this is bad" doesn't convey whether the bug is exploitable from across the internet by anonymous attackers, or only by a logged-in admin physically in your data centre.

**SARIF** — *[Static Analysis Results Interchange Format](https://sarifweb.azurewebsites.net/).* A JSON schema that essentially every SAST tool can emit. *Why it exists:* so you can run six different scanners, get six SARIF files, and merge them into one deduplicated view — instead of writing a custom parser for every tool.

**Taint / source / sink** — Vocabulary from dataflow analysis. A *source* is where untrusted data enters your program (an HTTP parameter, a network read, a CLI argument). A *sink* is somewhere that data shouldn't reach in raw form (a SQL `execute`, a shell command, an `eval`). Data is *tainted* if it came from a source and hasn't been *sanitised* on the way to a sink. *Why this vocabulary exists:* because almost every injection-class bug fits this shape, and once you can express it formally, you can find instances mechanically.

That's the core glossary. We'll introduce anything else as it comes up.

---

## The four pillars of modern attack surface coverage

Any serious security pipeline rests on four complementary techniques, each catching a different class of bug because each is sensitive to a different kind of evidence. Think of them less as redundant layers and more as four people in a room who each see a different part of the elephant.

1. **Static pattern analysis.** Fast, language-aware, finds structural problems by looking at the *shape* of source code (Post 2). Cheap enough to run on every commit.
2. **Dataflow-aware static analysis.** Slower, more thorough, finds bugs that span multiple functions by tracing how data actually moves through your program (Post 3).
3. **Coverage-guided fuzzing.** Finds crashes that static analysis can't reason about, by actually running the code with millions of mutated inputs (Post 5).
4. **Dynamic web application testing.** Hits running endpoints with crafted inputs to find issues that only manifest against a live service.

Each one has a fundamentally different cost and confidence trade-off:

| Technique | Setup cost | Per-finding confidence | What it misses |
|---|---|---|---|
| Pattern matching | Seconds | Medium — many false positives | Bugs requiring multi-step data flow |
| Dataflow | Minutes (often needs build) | High when path exists | Bugs requiring runtime state |
| Fuzzing | Hours | Very high — has a crashing input | Bugs not on instrumented paths |
| Dynamic web testing | Variable | High when reproducible | Logic flaws, auth bypasses |

![The four pillars positioned by setup cost and per-finding confidence, with each pillar's dominant blind spot called out.](diagrams/01-four-pillars-quadrant.svg)
*Figure 1 — The same trade-offs as a quadrant: cheaper pillars sit lower-left, higher-confidence ones upper-right. The label inside each bubble is what that pillar **can't** see, which is why running only one of them leaves obvious gaps.*

A team running only one of these has blind spots that are obvious in retrospect. A team running all four ends up with a different problem: an enormous combined output that nobody can triage.

That second problem is what the rest of the series is really about.

---

## Where the AI fits — and how it usually fails

The traditional pipeline runs these tools, dumps the union of their findings into a JSON file, and ships it. The output is roughly: *"here are 4,000 things that might be problems; you figure out which ones matter."*

The natural instinct is to point an LLM at this pile and ask "which ones are real?" When teams try it, they run into the same failure modes, almost without exception:

- **Confident false confirmations.** The model pattern-matches the alert against patterns it saw in training and produces a confident-sounding answer that's just wrong.
- **Missed real bugs.** The model sees a sanitiser call somewhere in the file and assumes it's protective — without checking whether it's actually on the path to the sink.
- **Inconsistent verdicts.** Two findings of the same CWE in the same codebase get rated wildly differently because each is analysed independently.
- **Hallucinated fixes.** The model "fixes" the bug by calling a helper function that doesn't exist in the codebase.

The root cause of all four is the same: one prompt is being asked to do many distinct cognitive jobs at once — verify the bug, trace its reachability, weigh exploitability, assign severity, propose a fix. End-to-end prompting on multi-step problems produces messy outputs. This is now well-documented in the LLM literature, and the architectural answer is **stage decomposition** — splitting the work into narrow stages with verifiable outputs, with deterministic checks between them.

We'll spend an entire post on what that pipeline looks like in practice (Post 7). For now, just hold the shape: the LLM should only be invoked on findings that have already passed cheaper, more reliable checks — and its outputs need to be verified by a *separate* stage with fresh context.

---

## For the AI/ML engineers reading this

Three patterns from this series generalise well beyond security tooling:

- **Mechanical pre-filtering before LLM invocation.** Anywhere your LLM is doing something a cheaper deterministic tool could do, use the tool. We'll see SMT solvers used this way in Post 4.
- **Separate generators from verifiers, with fresh contexts.** An LLM asked to verify the reasoning it just produced will say yes far too often. An LLM in a fresh context asked to check a specific claim against ground truth gives much better signal. Post 7 makes this concrete.
- **Calibrated outputs over binary classifiers.** "Exploitable / not exploitable" loses information that downstream decision-makers need. A richer verdict vocabulary — "confirmed but blocked by mitigations," "exploitable in principle but constrained" — survives the trip from pipeline to operator.

---

## What the rest of the series covers

The first four posts are tool-agnostic — they're about the *techniques* and why they work. The last four get into how a real framework wires them together end-to-end.

- **Post 2 — Semgrep and pattern matching.** What makes a pattern matcher better than `grep`, what categories of bug it catches well, and where it stops being useful.
- **Post 3 — CodeQL and dataflow analysis.** Why pattern matching has fundamental limits, and how taint tracking finds bugs that span multiple functions.
- **Post 4 — Z3 and SMT solvers.** Constraint solving from first principles, with worked examples of how a solver kills false positives that would otherwise eat hours of analyst time.
- **Post 5 — AFL++ and coverage-guided fuzzing.** Where static analysis ends, and the first post in the series where we look at a specific open-source framework that wires all of this together.
- **Post 6 — Binary exploit feasibility.** What separates "the program crashed" from "the program is exploitable" — and why these are wildly different things.
- **Post 7 — The LLM validation pipeline.** Eight-stage structured scepticism. The single most generalisable post in the series for AI/ML engineers.
- **Post 8 — Putting it together, honestly.** The full pipeline, plus a candid section on where these tools still fail.

By the end you should be able to build (or evaluate) a modern security analysis pipeline with calibrated confidence about what each layer adds and where each layer breaks.

---

## Next in series

- [Post 2 — Pattern Matching at Scale](./02-semgrep-pattern-matching.md). Why a regex isn't enough, and what an AST-aware pattern matcher actually does.

## Sources and further reading
- *[MITRE CWE](https://cwe.mitre.org/) — the canonical vulnerability-class taxonomy*
- *[FIRST CVSS 3.1 specification](https://www.first.org/cvss/v3.1/specification-document) — how severity vectors decompose*
- *[OASIS SARIF specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html) — the interchange format that makes multi-scanner pipelines possible*
- *[OWASP Top 10](https://owasp.org/Top10/) — the curated list of the most impactful web vulnerability classes*
