# Putting It All Together — Honestly

> Part 8 of 8. The full pipeline walked through with real vulnerable-code examples, followed by a candid section on what these tools still can't do. If the previous seven posts have sounded too good to be true, this post is the antidote.

---

Here's something I've noticed about security tooling demos: they always end at the moment of discovery.

The scanner finds the bug. The LLM produces a beautiful analysis. Everyone applauds. The demo ends.

What the demo skips is everything that happens next. What percentage of those findings survive closer scrutiny? Where does the pipeline quietly fall apart? What does "this is a known limitation" actually look like in practice?

This final post is the one where I stop making the pipeline sound polished. We'll walk through it with real examples first — Python, JavaScript, and C — and then I'll spend a substantial chunk of time on the honest limitations section that I think every serious practitioner deserves.

---

## Series navigation

- Understanding AI-Native Security (Part 1): What this all actually means — and a vocabulary primer (done!)
- Understanding AI-Native Security (Part 2): Pattern Matching at Scale — Why a regex isn't enough (done!)
- Understanding AI-Native Security (Part 3): Dataflow Analysis — When pattern matching isn't enough (done!)
- Understanding AI-Native Security (Part 4): SMT Solvers and the Math of Killing False Positives (done!)
- Understanding AI-Native Security (Part 5): Fuzzing, and Where RAPTOR Enters the Story (done!)
- Understanding AI-Native Security (Part 6): Binary Exploit Feasibility — From crash to constraints (done!)
- Understanding AI-Native Security (Part 7): The LLM Validation Pipeline (done!)
- **📌 Understanding AI-Native Security (Part 8): Putting It All Together — Honestly (this blog post!)**

---

## In this post

- The full `/agentic` pipeline as a single command — what happens when you pull the trigger
- A worked Python example: SQL injection traced through every stage
- A JavaScript example: XSS, eval, and a ReDoS bug worth highlighting
- A C example: integer overflow catching Z3 at its best
- The false-positive taxonomy — why "not exploitable" needs a reason
- Software Composition Analysis (SCA) — the supply-chain pillar
- An honest limitations section covering every layer of the pipeline

---

## The pipeline as a single command

`/agentic` is RAPTOR's one-command full-pipeline workflow. When you run it against a target, here's what happens:

![Parallel scanners feed merge/dedupe, which feeds the LLM validation stages, which feed Stage E (binary feasibility, conditional) and Stage F (cross-check) and finally the report. Optional --consensus / --judge / --exploit / --patch hang off as dashed post-processors; an optional /understand pre-step feeds the merge layer.](diagrams/08-putting-together.png)
*Figure 1 — The full orchestration. Solid path always runs; dashed paths are opt-in flags. Scanners on the left are parallel; everything downstream is sequential and gated by the previous stage. Real-time cost tracking applies to every stage, and `--budget N` stops the pipeline gracefully at $N rather than truncating silently.*

The scanners run in parallel. Their SARIF outputs merge and deduplicate. The merged inventory feeds the LLM validation pipeline (Posts 4 and 7). Binary memory-corruption findings additionally route through Stage E feasibility analysis (Post 6). Stage F catches contradictions. Stage 1 emits the final report.

The whole thing runs with real-time cost tracking. If you set `--budget 5.00` and the analysis is about to exceed five dollars of LLM spend, it stops gracefully and reports what it has — no silent truncation.

The next sections walk through concrete examples — Python, JavaScript, and C — showing how a single finding moves through every stage. Then comes the honest part.

---

## Python: a Flask app full of classics

The file `test/data/python_sql_injection.py` is a deliberately vulnerable Flask app the test suite uses to exercise the pipeline. We'll walk one example end-to-end, then summarise the others.

### Worked example: SQL injection

```python
@app.route('/user/<user_id>')
def get_user(user_id):
    db = sqlite3.connect(':memory:')
    cursor = db.cursor()

    # Direct string concatenation — SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
```

**Semgrep**: fires on the `injection/` rules. String concatenation flowing into `cursor.execute()` is a textbook pattern match. SARIF output tagged CWE-89.

**CodeQL**: independently traces the dataflow. `user_id` originates from a Flask route binding (a known taint source), flows through the `+` concatenation, reaches `cursor.execute()` (a known sink). Full source-to-sink path emitted.

**Dedup layer**: merges both findings into one canonical CWE-89 entry.

**Stage A**: LLM confirms the pattern is real. `user_id` comes directly from the URL with no sanitisation between source and sink.

**Stage B**: Attack path traced end-to-end. Entry point: `GET /user/<user_id>`. No type coercion, no parameterised query, no allowlist. Proximity score: **9/10** (10 reserved for cases that also require zero interaction or special timing).

**Stage C** (fresh-context verifier): Source code re-read verbatim. Stage B's claim "no sanitisation between source and sink" is checked against the actual call chain. Confirmed. The Stage B claim "Flask route binding produces a string" is checked against Flask documentation behaviour. Confirmed.

**Stage D**: Verdict: **exploitable**. CVSS vector: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` — network-accessible, no auth, full data compromise possible. Classic UNION-based or blind boolean injection applies.

**Stage F** (second fresh-context verifier): No contradictions. The vector matches the verdict and the verdict matches Stage B's proximity.

The four other findings in this file (command injection, MD5 password hashing, path traversal, hardcoded credential) follow the same pipeline shape. Each is caught by one or both scanners, validated through Stage A–D, and emerges with a verdict and CVSS vector.

### Summary table for the Python examples

| Finding | CWE | Stage D verdict | CVSS axes that matter |
|---|---|---|---|
| SQL injection via concatenation | CWE-89 | exploitable | `AV:N/PR:N/C:H/I:H/A:H` |
| Command injection via `shell=True` f-string | CWE-78 | exploitable | Unauthenticated RCE |
| MD5 used for password hashing | CWE-327 | confirmed | Critical for credential theft scenarios |
| Path traversal via Flask route binding | CWE-22 | exploitable | Arbitrary file read |
| Hardcoded credential | CWE-798 | exploitable | Any source-access compromises auth |

The MD5 case is interesting because it's "confirmed" rather than "exploitable" — the bug is real and severe in any compromise scenario, but it's not directly exploitable without an additional vulnerability that exposes the hashes. The verdict vocabulary preserves this distinction.

---

## JavaScript: the browser attack surface

`test/data/javascript_xss.js` exercises common web frontend bugs.

```javascript
function displayUserInput() {
    const userInput = document.getElementById('user_input').value;
    document.getElementById('output').innerHTML = userInput;
}
```

**Semgrep + CodeQL** both fire. CodeQL's DOM-XSS query traces `userInput` from the DOM source to the `innerHTML` sink.

**Stage B**: Payload `<img src=x onerror=alert(document.cookie)>`. No sanitisation, no `textContent` alternative. Browser executes in page origin context.

**Stage D**: **Exploitable**. Session hijacking, credential theft, keylogging, and CSRF token exfiltration are all achievable. CVSS: `AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N` — note `UI:R` (user interaction required: the victim has to load the page) and `S:C` (scope: changed — XSS in one origin can affect others).

Other findings in the same file:

| Finding | CWE | Notes |
|---|---|---|
| `document.write` with `URLSearchParams` | CWE-79 | Reflected XSS via crafted URL |
| `eval(code)` for user-supplied input | CWE-94 | Arbitrary code execution in page context |
| `Math.random()` for session tokens | CWE-330 | Predictable RNG — replace with `crypto.getRandomValues()` |
| Catastrophic regex for email validation | CWE-1333 | ReDoS — `O(2^n)` worst case on crafted input |

The ReDoS case is worth highlighting because it doesn't look like a security bug to most reviewers. A regex like `/^([a-zA-Z0-9]+)*@([a-zA-Z0-9]+)*\.([a-zA-Z0-9]+)*$/` has nested quantifiers on both sides of the `@`. An input like `"aaaaaaaaaaaaaaaaaaa@"` (no valid domain part) causes the engine to try every possible way to partition the `a` sequence — exponential worst-case matching time. On a server endpoint that runs this regex per-request, a single packet is a denial of service. Don't worry if that feels surprising — the pattern is very non-obvious until you see it the first time.

---

## C: where Z3 earns its keep

The Z3 testbench from Post 4 walks all eight cases. Here's how one of them looks end-to-end with the full pipeline.

### Worked example: integer overflow → heap overflow

```c
void case_alloc_overflow(unsigned int count) {
    unsigned int alloc_size = count * RECORD_SIZE;

    if (count >= MAX_RECORDS) { return; }
    if (alloc_size >= MAX_ALLOC) { return; }

    record_t *records = malloc(alloc_size);
    for (unsigned int i = 0; i < count; i++) {
        memset(&records[i], 'A', RECORD_SIZE);
    }
}
```

**CodeQL**: identifies dataflow from `count` to the `memset` sink. Flags potential integer overflow leading to OOB write.

**Z3 pre-screening**: encodes the three constraints as bitvectors. SAT — `count = 0x10000001` satisfies all constraints. The concrete value is injected into the Stage A prompt.

**Stage A**: LLM confirms with the supplied `count` value. The arithmetic checks out; the bug is real.

**Stage B**: Attack path confirmed. The overflow produces a tiny heap buffer followed by an enormous write — a classic heap overflow primitive.

**Stage C** (fresh-context verifier): Source confirms the multiplication happens before the guards. Confirmed.

**Stage D**: Verdict: **exploitable** (when ASAN is off). CVSS: `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`.

**Stage E**: Binary feasibility analysis. Checks mitigations of the target binary. With ASAN, the crash is detected immediately (high signal, lower exploit weaponisation value). Without ASAN, heap metadata corruption opens the door to arbitrary write primitives via the allocator. Verdict refined: `exploitable` or `confirmed_constrained` depending on the environment.

The complete chain: CodeQL → Z3 → LLM Stage A (with PoC value) → Stage B → Stage C → Stage D → Stage E. Each stage adds information; none of them re-do the work of an earlier stage.

---

## The false-positive taxonomy

RAPTOR doesn't just say "not exploitable." It categorises *why*:

| Reason | Meaning |
|---|---|
| `sanitized_input` | Input filtering or escaping blocks exploitation |
| `dead_code` | The vulnerable code is unreachable |
| `test_only` | The vulnerability exists only in test infrastructure |
| `unreachable_path` | Preconditions required are impossible in practice |
| `safe_api_usage` | The API is used correctly despite the pattern match |
| `compiler_optimized` | Dead code elimination removes the issue |
| `defense_in_depth` | Additional controls block the attack path |

These categories matter for two reasons: **audit trails** (when a finding is dismissed, the reason is recorded, and a future reviewer can argue with the dismissal) and **scanner improvement** (aggregate statistics on dismissal reasons drive rule refinement).

---

## SCA: the supply-chain pillar

`/agentic` also runs Software Composition Analysis alongside the source scanners. RAPTOR queries:

- **[OSV](https://osv.dev/)** — the Open Source Vulnerability database
- **[NVD](https://nvd.nist.gov/)** — the National Vulnerability Database
- **Registry metadata** — PyPI, npm, Crates.io, RubyGems, Maven, Go modules, Composer, NuGet, Debian, Homebrew

It also runs supply-chain heuristics including [typosquat detection](https://blog.sonatype.com/this-week-in-malware-typosquats-in-pypi-dependency-confusion-packages) against declared dependencies. A malicious `reqeusts` package (with the transposed `qe`) in `requirements.txt` won't slip by unnoticed.

---

## Now the honest part: what doesn't work

If the previous seven posts have sounded like a polished story, this section is the corrective. Every technique we've covered has real limitations. Every layer of the pipeline has failure modes. A serious security practitioner will be sceptical of any tool that doesn't list its own gaps explicitly — so here are RAPTOR's, organised by which part of the pipeline they affect.

## Pattern matching has hard limits

**Intra-procedural by design.** Semgrep's rules see one function at a time. A bug like "tainted data passes through three helper functions before reaching the sink" is invisible. CodeQL covers this case, but Semgrep cannot — and a non-trivial fraction of real bugs are this shape.

**Pattern coverage skews toward known APIs.** Crypto rules catch `hashlib.md5` but miss a hand-rolled implementation that does MD5 explicitly. Rules need to be written for each API; novel or domain-specific APIs are unwatched until someone adds rules for them.

**Logic bugs are out of scope.** "This authorisation check should be present but isn't" requires reasoning about *absence*, which most pattern engines can't express. Authorisation bugs are among the most common high-severity issues in real codebases; no pattern matcher catches them.

## Dataflow analysis fails on build problems and metaprogramming

**Build extraction failures.** This is the single biggest practical problem with CodeQL. Empirically, anywhere from 10% to 30% of real repositories fail extraction on the first attempt — missing dependencies, environment-specific toolchains, vendored libraries, custom build wrappers, code generation steps that need to run first. RAPTOR's build detector handles common cases (Maven, Gradle, npm, cargo, cmake) but cannot rescue an arbitrarily broken build. When extraction fails, you get partial coverage, and the partial-coverage warnings are easy to miss.

**Dynamic dispatch and metaprogramming confuse extraction.** Heavy use of Python decorators, JavaScript proxy objects, runtime class generation, dependency injection containers, ORM magic — all of these can cause CodeQL's call graph to be incomplete. The dataflow it reports is correct; the dataflow it *misses* is invisible.

**Slow.** CodeQL extraction can take minutes to hours on large codebases. This rules it out of the inner loop (per-commit / per-PR) for sizeable projects. Most teams run CodeQL nightly, not on every change.

## SMT pre-screening has narrow applicability

**Function-call conditions kill the parse.** Anything like `if (validate(x) && x > 0)` becomes indeterminate because Z3 can't reason about `validate`. The framework falls back to LLM analysis on these, which means the cost savings only apply when path conditions are pure arithmetic or pointer-nullness.

**High-level CWEs don't benefit.** SMT pre-screening adds essentially zero value for SQL injection, XSS, authorisation bugs, or anything whose precondition isn't expressible as a numeric constraint. The sweet spot — CWE-190 / CWE-120 / CWE-122 / CWE-193 / CWE-476 — is real but narrow.

**The encoding is approximate.** Translating C semantics into bitvector logic is mostly correct, but corner cases exist (pointer arithmetic on uninitialised memory, certain undefined-behaviour interactions). The framework is conservative: when in doubt it returns `feasible=None` rather than risk a false UNSAT.

## Fuzzing has well-known gaps

**Stateful protocols are painful.** Vanilla AFL++ does poorly on multi-round network protocols, session-based authentication, or anything that requires state setup before the interesting bug is reachable. Structured fuzzing helps (libProtobuf-Mutator, custom grammars) but isn't built into the current framework.

**Deeply structured input formats need grammars.** A fuzzer pointed at a complex JSON-RPC service mostly produces invalid input that's rejected at the parsing stage. Coverage in the application logic remains shallow.

**Setup is heavy.** Compiling a target with instrumentation, preparing a seed corpus, configuring sanitisers — each step can fail in environment-specific ways. The framework automates much of this, but "automates" means "tries"; non-trivial projects still need manual intervention.

**You stop when you run out of patience, not when you're done.** Fuzzing has no natural termination condition. The corpus keeps growing slowly forever. Coverage curves go logarithmic. The decision to stop is operational, not mathematical.

## Binary exploit feasibility analysis is heuristic

**Mitigations check what's *declared*, not what's *enforced*.** A binary's ELF headers can say "Full RELRO" while the loader policy on the deployment host is more permissive (or vice versa). The framework reports the static facts; runtime behaviour may differ.

**Gadget quality is hard to assess statically.** The framework counts usable gadgets, but "usable in this specific exploit scenario" requires knowing the constraints on register state at the point of hijack, which the framework can only approximate from crash state.

**Verdicts are predictions, not guarantees.** A `confirmed_blocked` finding might still be exploitable by a researcher with novel techniques. A `likely exploitable` finding might fail in practice for reasons the analysis missed. The framework optimises for honest calibration, not certainty.

## The LLM stages still hallucinate

This is the one most worth saying out loud, because the seven previous posts have argued that staged decomposition and fresh-context verification *reduce* hallucination. They do — but they don't eliminate it.

**Stage C catches drift but not invention.** If Stage B claims `validateInput` exists and Stage C reads the file and confirms a function with that name exists, Stage C signs off — even if the *behaviour* of `validateInput` is being misrepresented. Verifying behaviour requires more careful prompts than verifying existence, and even then is sometimes wrong.

**Stage F catches contradictions but not consistent errors.** If every stage is wrong in the same direction (all confirming an exploit path that doesn't exist), Stage F won't catch it because the outputs agree with each other.

**Multi-model consensus reduces but doesn't eliminate correlated failures.** If two models share training data, they share blind spots. Truly independent samples are hard to get.

**Costs accumulate fast.** A multi-model run with consensus + judge can be 4–6× the cost of a single-model run. Budget cutoffs help, but realistic security analyses on large codebases still run into hundreds of dollars per scan. This is a real obstacle to adoption.

## Operational concerns the framework can't solve

**Models drift.** A prompt that works well with one model version may degrade with the next release. Maintenance is ongoing.

**Cost projections are unreliable until you've run on your codebase.** The framework tracks cost accurately but can't predict it in advance — different codebases produce wildly different finding densities.

**False negatives are the unmeasured failure.** Every metric in this post is about findings that *were* produced. Findings that weren't produced (real bugs the pipeline missed entirely) are by definition invisible. No combination of tools achieves 100% recall; the best you can do is run multiple complementary techniques and accept that some real bugs will still slip through.

**The web pillar is alpha.** The dynamic web scanner (crawler + input fuzzer + ffuf + vuln scanner) is the least mature of the four pillars. It works for simple targets but requires significant manual configuration for anything with non-trivial auth, multi-step workflows, or single-page-app routing.

**Exploit generation and patch generation are beta.** The `--exploit` and `--patch` flags produce useful starting points, not finished artefacts. Generated PoCs need verification; generated patches need code review. Treat the outputs as a draft, not a deliverable.

---

## What this all means in practice

The honest pitch for a framework like this is *not* "you don't need humans anymore." It's: **the tools do the tedious, parallelisable, well-defined parts of security analysis so the human can spend time on the hard, judgement-heavy parts**. Triage, prioritisation, prose explanation, dataflow tracing across documented functions, mitigation enumeration — these are appropriate work for the pipeline. Exploit development, novel vulnerability research, weighing organisational risk, designing the *next* mitigation — these remain firmly human work.

The validation pipeline doesn't replace a senior security engineer. It saves a senior security engineer from having to read 4,000 scanner alerts to find the 12 that matter. That's not glamorous and it doesn't make a great vendor demo, but it's where the real productivity gain lives.

For AI/ML engineers, the meta-lesson is the same one as Post 7's headline: **stage-decompose, use fresh-context verifiers, gate probabilistic stages with deterministic ones, preserve calibrated uncertainty in your outputs, and be candid about limitations**. The architectural patterns generalise. The honesty about gaps is what builds enough trust to get the tools used at all.

That's the series. If you've stayed all the way through, thanks for reading.

---

*The full series:*
- *[Part 1 — Introduction to AI-Native Security Research](./01-introduction-ai-native-security.md)*
- *[Part 2 — Pattern Matching at Scale](./02-semgrep-pattern-matching.md)*
- *[Part 3 — Dataflow Analysis](./03-codeql-dataflow-analysis.md)*
- *[Part 4 — SMT Solvers and Killing False Positives](./04-z3-smt-solver-filtering.md)*
- *[Part 5 — Fuzzing, and Where RAPTOR Enters](./05-afl-coverage-guided-fuzzing.md)*
- *[Part 6 — Binary Exploit Feasibility](./06-binary-exploit-feasibility.md)*
- *[Part 7 — The LLM Validation Pipeline](./07-llm-validation-pipeline.md)*
- *Part 8 — Putting It Together, Honestly (you are here)*

## Sources and further reading
- *[OSV](https://osv.dev/) — the Open Source Vulnerability database; the canonical source for ecosystem-aware vulnerability lookups.*
- *[NVD](https://nvd.nist.gov/) — the NIST National Vulnerability Database.*
- *Klees et al., ["Evaluating Fuzz Testing"](https://dl.acm.org/doi/10.1145/3243734.3243804) — CCS 2018. The paper that documented how many fuzzing comparisons were statistically meaningless; a useful cautionary read for anyone evaluating security tools.*
- *Christakis & Bird, ["What Developers Want and Need from Program Analysis: An Empirical Study"](https://www.microsoft.com/en-us/research/publication/what-developers-want-and-need-from-program-analysis-an-empirical-study/) — ASE 2016. Empirical work on why developers ignore static-analysis output; the false-positive economics that any production pipeline has to confront.*
