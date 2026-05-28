# SMT Solvers and the Math of Killing False Positives

> Part 4 of 8. Why constraint solvers exist, what they actually do, and how using one in front of an LLM pipeline saves analysts hours per scan.

---

Let me start with a puzzle. Not a security puzzle — an actual puzzle.

You've got a Sudoku grid in front of you. 81 cells, 30 of them already filled in. The rules: each row, each column, and each 3×3 box must contain the digits 1–9 with no repeats. Your job is to find values for the remaining 51 empty cells.

What you're doing — formally — is *constraint satisfaction*. You have a set of variables (the empty cells), each with a finite domain (1–9), and a set of constraints (the row/column/box rules). You're looking for an assignment that satisfies all constraints simultaneously. If you find one, the puzzle is *satisfiable* (SAT). If you can prove no assignment exists — say, two of the pre-filled cells already contradict each other — the puzzle is *unsatisfiable* (UNSAT).

Here's the thing: every security pipeline has a Sudoku problem hiding inside it.

---

## Series navigation

- Understanding AI-Native Security (Part 1): What this all actually means — and a vocabulary primer (done!)
- Understanding AI-Native Security (Part 2): Pattern Matching at Scale — Why a regex isn't enough (done!)
- Understanding AI-Native Security (Part 3): Dataflow Analysis — When pattern matching isn't enough (done!)
- **📌 Understanding AI-Native Security (Part 4): SMT Solvers and the Math of Killing False Positives (this blog post!)**
- Understanding AI-Native Security (Part 5): Fuzzing, and Where RAPTOR Enters the Story (coming soon!)
- Understanding AI-Native Security (Part 6): Binary Exploit Feasibility — From crash to constraints (coming soon!)
- Understanding AI-Native Security (Part 7): The LLM Validation Pipeline (coming soon!)
- Understanding AI-Native Security (Part 8): Putting It All Together — Honestly (coming soon!)

---

## In this post

- What SMT solvers are and why they exist
- Why a security pipeline cares about constraint solving
- Bitvector arithmetic — how SMT solvers model C semantics exactly
- Three groups of real cases: SAT (bugs found), UNSAT (false positives killed), and Indeterminate (graceful fallback)
- A worked decision matrix showing the full economics
- The engineering pattern that generalises way beyond security

---

## What SMT solvers actually do

An [SMT solver](https://en.wikipedia.org/wiki/Satisfiability_modulo_theories) does the same thing as our Sudoku solver, but for arbitrary logical formulas over arbitrary mathematical *theories*: integer arithmetic, bitvectors, arrays, real numbers, strings. Give it a formula, and it tells you SAT (with a witness assignment that satisfies it) or UNSAT (with a proof that no assignment can exist).

**Why SMT solvers exist:** because a huge class of real-world questions — "is this program path reachable?", "is this hardware design correct?", "is this scheduling problem feasible?" — reduces to constraint satisfaction. Once you have a general-purpose constraint solver, every such question can be answered mechanically.

[Z3](https://github.com/Z3Prover/z3), developed at Microsoft Research by Leonardo de Moura and Nikolaj Bjørner ([TACAS 2008 paper](https://www.microsoft.com/en-us/research/publication/z3-an-efficient-smt-solver/)), is the most widely deployed SMT solver in the world. It's MIT-licensed, has bindings in every major language, and is the de-facto choice for program verification, symbolic execution, and security analysis.

---

## Why a security pipeline cares about SMT

Recall from Post 3 that a dataflow analyser outputs a structured path: source → through some intermediate nodes → to a sink. Along the way, the path may pass through one or more conditional branches. Each branch imposes a *path condition* on the variables.

Now ask the question: *for this path to actually be executable, do there exist input values that satisfy all the path conditions simultaneously?*

If the answer is no — the conditions are mutually contradictory — then the path is **dead code**. The dataflow tool flagged it (correctly, as a syntactic dataflow), but it can never execute in practice. The finding is a false positive.

If the answer is yes, then not only is the path reachable, but the solver hands you specific input values that reach it. **Those values are a candidate proof-of-concept.**

Either way, you've extracted enormous value before any expensive analysis stage runs. UNSAT means *don't waste the analyst's time*. SAT means *here's the input, the analyst's job is much easier*.

This is the engineering trick. **Cheap deterministic solver in front; expensive probabilistic reasoner (human or LLM) behind.** It's one of the cleanest examples in applied AI of using a classical tool to make an LLM tool faster and more reliable.

---

## Bitvector arithmetic: matching C semantics

Here's something that trips up most developers: when you do math in C with `unsigned int`, you're not working with ordinary mathematical integers. You're working with a 32-bit counter that **wraps around** — like an odometer that rolls over from 999,999 back to 0.

The 32-bit limit is 4,294,967,295. If you add 1 to that, you get 0. If you multiply two numbers whose product exceeds that limit, the result wraps back to `product - 4,294,967,296`.

When we encode C code in Z3, we use **bitvectors** to model this wrap-around behaviour exactly. Z3 supports a dedicated theory for this — [QF_BV](https://smt-lib.org/logics-all.shtml#QF_BV) — that makes `unsigned int` overflow behave exactly as it does in real C code.

This matters because the most interesting bug class in C (integer overflow leading to memory corruption) only exists *because* of wraparound. If we modelled C's `unsigned int` as a regular mathematical integer, the overflow would never appear. Bitvector logic preserves it — which is exactly what we want.

---

## Three groups of cases worth walking through

To make the SAT/UNSAT story concrete, here are eight C cases drawn from a purpose-built test corpus designed to exercise every interaction between a dataflow tool, an SMT solver, and a downstream analyst. They fall into three groups:

1. **SAT** — real bugs the solver finds and hands the analyst a PoC for
2. **UNSAT** — false positives the solver kills before anyone wastes time
3. **Indeterminate** — cases the solver can't reason about, which fall through to full manual or LLM analysis

### Group 1: SAT — the bugs the solver finds for you

**Case 1a: integer overflow → heap overflow (CWE-190 → CWE-122)**

```c
#define MAX_RECORDS  1000000000u  // 1 billion — max allowed count
#define MAX_ALLOC       32768u   // 32 KB — max allowed allocation
#define RECORD_SIZE        16u

void case_alloc_overflow(unsigned int count) {
    // BUG: this multiply runs BEFORE the guards below — and can wrap
    unsigned int alloc_size = count * RECORD_SIZE;

    if (count >= MAX_RECORDS) { return; }    // guard 1: reject huge counts
    if (alloc_size >= MAX_ALLOC) { return; } // guard 2: reject huge allocations

    record_t *records = malloc(alloc_size);
    for (unsigned int i = 0; i < count; i++) {
        // writes count × 16 bytes — but the buffer is only alloc_size bytes
        memset(&records[i], 'A', RECORD_SIZE);
    }
}
```

The function looks safe. Two guards are supposed to bound `count` and `alloc_size`. The trap is ordering: `count * RECORD_SIZE` is computed *before* the guards run. If the product wraps, `alloc_size` becomes a small number that passes both guards — while `count` stays enormous.

The solver encodes the three conditions that must all hold simultaneously:
```
count < 1,000,000,000      ; guard 1 passes (count is not huge)
alloc_size < 32,768        ; guard 2 passes (allocation looks small)
alloc_size == count * 16   ; the multiply, with 32-bit wrap-around
```

Z3 returns SAT with **`count = 268,435,457`** (roughly 268 million).

Here's the math: `268,435,457 × 16 = 4,294,967,312`. The 32-bit limit is 4,294,967,295, so this wraps to `4,294,967,312 − 4,294,967,296 = 16`. Both guards see a count of 268M (under 1B ✓) and an allocation of 16 bytes (under 32,768 ✓). `malloc(16)` allocates 16 bytes. The loop then writes `268,435,457 × 16 ≈ 4 GB` into that 16-byte buffer.

That `count = 268,435,457` value can be injected directly into whatever analyst process runs next — a human reviewer, an LLM prompt, a fuzzer's seed input. The downstream analyst doesn't have to figure out the overflow arithmetic — the solver already proved it. Their job is now to reason about exploitability and impact.

**Case 1b: unsigned sum overflow — bounds check bypass (CWE-190 → CWE-120)**

```c
// buffer_size = 64
if (offset + length <= buffer_size) {            // sum can wrap silently
    memcpy(shared_buffer + offset, src, length); // writes 'length' bytes at 'offset'
}
```

The check looks right — it rejects writes that go past the buffer. But `offset + length` is unsigned 32-bit arithmetic. If the two values add up to more than 4,294,967,295, the sum wraps to a small number that passes the check.

Z3 finds: `offset = 4,294,901,760`, `length = 65,552`. Their sum is `4,294,967,312`, which wraps to **16**. The check sees `16 ≤ 64` and passes. `memcpy` then writes 65,552 bytes starting at an offset of ~4 billion bytes past the buffer. The signed/unsigned-confusion class of bug, captured deterministically.

**Case 1c: off-by-one — `<=` where `<` was meant (CWE-193)**

```c
#define INDEX_LIMIT 128

if (index > INDEX_LIMIT) { return; }  // BUG: should be >= to also reject 128
buf[index] = value;                   // reachable when index == 128 (one past the end)
```

The guard uses `>` instead of `>=`, so `index == 128` slips through and writes one byte past the end of the buffer. Z3 trivially finds `index = 128`. The kind of off-by-one humans miss on a tired afternoon — the solver finds it in microseconds.

### Group 2: UNSAT — the false positives the solver kills

These three cases are dataflow paths a tool correctly identifies as syntactically valid source-to-sink flows, but whose path conditions are mathematically impossible.

**Case 2a: value range contradiction**

```c
if (x <= 100) { return; }   // x must be > 100 to get past here
if (x >= 50) {              // always true when x > 100
    if (x < 50) {           // impossible: x can't be both > 100 and < 50
        strcpy(dead_buf, data);
    }
}
```

Z3 encodes `x > 100 ∧ x < 50`, returns UNSAT. Finding discarded.

**Case 2b: pointer nullness contradiction**

```c
if (ptr == NULL) { return; }  // ptr is non-null past here
if (ptr != NULL) {
    strncpy(dst, ptr, 32);    // safe path
} else {
    strcpy(dst, ptr);         // ptr can't be both non-null AND null — impossible
}
```

UNSAT in microseconds. Discarded.

**Case 2c: bitmask contradiction**

```c
if (flags & 0x1) { return; }    // bit 0 is 0 past here (flag not set)
if ((flags & 0x1) == 1) {       // bit 0 must be 1 — contradicts the line above
    ...
}
```

A single bit can't be both 0 and 1. UNSAT. Discarded.

**The economics of these three cases**: without the solver, each would be a full review ending in "false positive — branches are mutually exclusive." With the solver, each is gone in microseconds, never reaches an LLM or human, and never appears in the operator's report. Across a large codebase this is the difference between a clean inventory and a noisy pile.

### Group 3: indeterminate — graceful degradation

Some path conditions can't be encoded in bitvector arithmetic. Function calls are the most common reason — the solver can't reason about `strlen(input)` or `validate(ptr)` without knowing what those functions do.

**Case 3a: function call in condition**

```c
if (strlen(input) < sizeof(local)) {
    strcpy(local, input);
}
```

The solver's parser sees `strlen(input)` and gives up. Returns `feasible=None`. The framework treats this as "we couldn't pre-screen this one" and full analysis runs unchanged.

**Case 3b: partial parse, mixed conditions**

```c
if (size >= sizeof(buf)) { return; }    // parseable: size < 256
if (validate(ptr)) {                    // unparseable: solver doesn't know what validate() does
    memcpy(buf, ptr, size);
}
```

One condition parses, one doesn't. Solver returns `feasible=None`. Full analysis runs.

The key design choice: **indeterminate is never treated as UNSAT**. The framework is conservative — when the solver doesn't know, the LLM/analyst still gets a chance. The cost is one analysis call per indeterminate case; the alternative would be silently dropping potentially-real findings, which is the failure mode you really want to avoid.

---

## The decision matrix in practice

| Finding type | Solver result | Action |
|---|---|---|
| Case 1a (alloc overflow) | SAT — `count = 268,435,457` | PoC injected into analyst's input; full review runs |
| Case 1b (sum overflow) | SAT — `offset = 4,294,901,760, length = 65,552` | PoC injected; full review |
| Case 1c (off-by-one) | SAT — `index = 128` | PoC injected; full review |
| Case 2a (range) | UNSAT | Discarded |
| Case 2b (nullness) | UNSAT | Discarded |
| Case 2c (bitmask) | UNSAT | Discarded |
| Case 3a (`strlen` call) | None (unparseable) | Full review runs |
| Case 3b (`validate` call) | None (partial parse) | Full review runs |

![Each CodeQL finding's path conditions are handed to Z3, which returns SAT (with a witness), UNSAT, or indeterminate — each routed to a different downstream action.](diagrams/04-smt-solver.png)
*Figure 1 — The three-way decision visualised. SAT pulls the witness values into the LLM prompt as a free PoC; UNSAT kills the finding before any expensive analysis runs; indeterminate gracefully degrades to full LLM review with a warning. The framework never silently drops a finding it couldn't reason about.*

The empirical sweet spot for SMT pre-screening is **CWE-190 (integer overflow), CWE-120 / CWE-122 (buffer overflows), CWE-193 (off-by-one), and CWE-476 (null pointer dereference)**. These are exactly the CWEs whose preconditions reduce naturally to bitvector or pointer-nullness constraints.

For higher-level CWEs (logic flaws, authorisation bypasses, XSS), SMT pre-screening doesn't help — the constraints aren't expressible in QF_BV without modelling the entire surrounding world. That's where LLMs or human reviewers earn their keep.

---

## Why this matters as a pattern beyond security

If you're an AI/ML engineer, the lesson generalises cleanly:

- **Identify the cheap-deterministic / expensive-probabilistic boundary.** SMT solvers are cheap and deterministic; LLMs are expensive and probabilistic. A few milliseconds in the solver avoids dollars and seconds in LLM calls.
- **Let the cheap stage produce input for the expensive stage.** SMT doesn't just gatekeep; it produces concrete witness values when satisfiability holds. Those values make the LLM's job easier — fewer reasoning steps, smaller chance of hallucination.
- **Make degradation explicit.** When the solver can't reason about a constraint, the pipeline shouldn't lie about it. `feasible=None` is a first-class result, plumbed through the rest of the system, visible to the operator.
- **Treat false positives as engineering work, not noise.** Every false-positive class is a place to deploy a specific filter. Pattern-condition contradictions get SMT. Test-only code gets a static check. Sanitised inputs get a dedicated disqualifier. Each filter is a deliberate engineering choice with measurable impact.

The general principle: **anywhere your LLM is doing something a deterministic solver could do, replace it.** The LLM is for the parts where there is no solver — judgement, prose generation, weighing competing considerations.

---

## Next in series

- [Post 5 — AFL++: Coverage-Guided Fuzzing](./05-afl-coverage-guided-fuzzing.md). The next post is also where we introduce the open-source framework that wires together everything we've covered.

## Sources and further reading
- *de Moura & Bjørner, ["Z3: An Efficient SMT Solver"](https://www.microsoft.com/en-us/research/publication/z3-an-efficient-smt-solver/) — TACAS 2008. The original paper; still the clearest short explanation of how Z3 combines theory solvers.*
- *[Z3 GitHub repository](https://github.com/Z3Prover/z3) — implementation, language bindings, and a tutorial in the wiki.*
- *Cadar & Sen, ["Symbolic Execution for Software Testing"](https://cacm.acm.org/research/symbolic-execution-for-software-testing-three-decades-later/) — Communications of the ACM, 2013. The best survey of how SMT solvers connect to program analysis, written by two of the people who pushed it forward.*
- *[SMT-LIB](https://smt-lib.org/) — the standard input format and theory specifications.*
