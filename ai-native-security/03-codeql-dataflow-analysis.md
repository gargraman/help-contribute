# Dataflow Analysis: When Pattern Matching Isn't Enough

> Part 3 of 8. Pattern matchers find bugs where the bad shape is on a single line. Dataflow analysers find bugs where every line looks fine but the composition is wrong.

---

I want to start this post with a bug that broke my brain the first time I saw it.

Look at this code:

```python
@app.route('/profile')
def profile():
    name = request.args.get('name')
    return render_user(name)

def render_user(name):
    decorated = decorate(name)
    return write_output(decorated)

def decorate(s):
    return f"<h1>{s}</h1>"

def write_output(html):
    return Response(html, mimetype='text/html')
```

There's a textbook XSS vulnerability buried in here. An attacker can inject arbitrary HTML by controlling the `name` parameter. But here's what's interesting — if you run a pattern matcher over this code, nothing fires. `request.args.get('name')` is fine. `f"<h1>{s}</h1>"` is fine. `Response(html, ...)` is fine. Every single line looks harmless on its own.

The bug is in the *composition*. The tainted value flows through three helper functions before it hits the response — and pattern matchers, by design, only look at one function at a time.

This is exactly the wall we talked about at the end of Post 2. And it's the reason an entire class of tools exists that works completely differently.

---

## Series navigation

- Understanding AI-Native Security (Part 1): What this all actually means — and a vocabulary primer (done!)
- Understanding AI-Native Security (Part 2): Pattern Matching at Scale — Why a regex isn't enough (done!)
- **📌 Understanding AI-Native Security (Part 3): Dataflow Analysis — When pattern matching isn't enough (this blog post!)**
- Understanding AI-Native Security (Part 4): SMT Solvers and the Math of Killing False Positives (coming soon!)
- Understanding AI-Native Security (Part 5): Fuzzing, and Where RAPTOR Enters the Story (coming soon!)
- Understanding AI-Native Security (Part 6): Binary Exploit Feasibility — From crash to constraints (coming soon!)
- Understanding AI-Native Security (Part 7): The LLM Validation Pipeline (coming soon!)
- Understanding AI-Native Security (Part 8): Putting It All Together — Honestly (coming soon!)

---

## In this post

- The class of bug that pattern matching can never catch — and why
- How dataflow analysers actually work (two phases: extraction and query)
- The source / sink / sanitiser model that almost every injection bug fits
- What languages CodeQL supports and what queries it ships
- The build problem — where dataflow setups fail most often in practice
- A worked SQL injection example traced all the way through
- The path-condition problem that sets up the next post

---

## The bug pattern matching can never catch

**Dataflow analysers exist because most non-trivial vulnerabilities span multiple functions, and you can't see them without tracing how data moves between those functions.**

The XSS example above is a clean illustration. The user-controlled `name` from `request.args` flows through three helper functions and ends up inside an HTML response without escaping. No Semgrep pattern fires on any single line: `request.args.get('name')` is fine, `f"<h1>{s}</h1>"` is fine, `Response(html, ...)` is fine. The bug is in the *composition*, not in any individual statement.

![Three functions across two files: a source, a helper that propagates taint via string concatenation, and a sink. The would-be sanitizer is missing.](diagrams/03-source-sanitizer-sink-trace.svg)
*Figure 1 — The classic source / sanitiser / sink shape applied to a multi-function trace. Pattern matching sees one function at a time and cannot connect the source to the sink through the helpers. Dataflow analysis builds the call graph during extraction and then asks: is there any source → sink path with no sanitiser on it?*

The canonical open-source tool in this category is [CodeQL](https://codeql.github.com/docs/), built by GitHub (originally Semmle). It powers GitHub Advanced Security and its query language is well-designed enough that the security community has invested heavily in writing queries for it.

---

## How a dataflow analyser actually works

A dataflow analyser operates in two phases. Don't worry if this feels a bit abstract at first — the worked example at the end will make it very concrete.

**Phase 1: extraction.** The tool compiles (or for interpreted languages, parses) your code and writes the resulting AST, control-flow graph, call graph, and type information into a *database*. The database is a relational store — tables of expressions, tables of functions, tables of calls, all joined on IDs. For Python and JavaScript this is just parsing; for Java, C++, or Go it means actually running your build system.

**Phase 2: query.** You write queries in the tool's query language (CodeQL uses QL, a Datalog-like declarative language). A query expresses a logical condition over the database, and the tool returns every match. For security purposes, the most important queries are **taint-tracking queries**: "find every flow from a source predicate to a sink predicate that doesn't pass through a sanitiser."

Run that against the XSS example above with `request.args.get` as a source and `Response(...)` as a sink, and CodeQL returns the full four-step flow: `request.args.get` → `name` → `render_user(name)` → `decorate(name)` → `f"<h1>{s}</h1>"` → `write_output(decorated)` → `Response(html, ...)`. Every link in the chain is verified against the actual code.

That's the headline feature. **It's why dataflow analysers catch a completely different class of bug than pattern matchers.**

---

## The source / sink / sanitiser model

Almost every dataflow vulnerability fits a three-part shape. Once you internalise this model, you'll start seeing it everywhere:

- **Source** — where untrusted data enters: `request.args`, `os.environ`, `socket.recv`, command-line args, deserialisation, file reads
- **Sink** — where untrusted data shouldn't reach in raw form: `cursor.execute` (SQLi), `subprocess.run(shell=True)` (command injection), `open(path)` (path traversal), `eval`/`exec` (code injection), `Response(html)` (XSS), `urllib.urlopen(url)` (SSRF)
- **Sanitiser** — a function that, when data passes through it, makes the data safe: HTML escapers, parameterised-query wrappers, allowlist validators, regex matchers that reject dangerous characters

The CodeQL security suite ships with curated source/sink/sanitiser catalogues for each supported language and each major vulnerability class. The taint-tracking query for SQL injection in Python knows that Django's `Model.objects.raw()` is a sink, that `cursor.execute(query, params)` *with the params form* is sanitised by parameterisation, and that values from `request.GET` are sources.

When a query reports a flow, it reports the **full path**: each intermediate node, with file and line number. That's the actionable artefact a downstream stage (or a human) can verify.

---

## Languages and what dataflow covers

CodeQL supports Java, C, C++, C#, Python, JavaScript, TypeScript, Go, Ruby, and Swift. The full security suite for each language includes queries for:

- Injection (SQLi, command injection, XSS, log injection)
- Buffer issues for C/C++ (overflows, underflows, off-by-one, OOB read/write)
- Authentication and authorisation bypasses
- Path traversal
- SSRF
- Deserialisation
- Cryptographic weaknesses with data-flow components (e.g., predictable keys derived from user input)
- Hardcoded credentials reaching authentication sinks

The trade-off versus pure pattern matching: dataflow analysis is more precise (when it reports a flow, the flow is real) and has more recall on multi-step bugs (it sees what pattern matching can't), but it's slower and — for compiled languages — needs your build system.

---

## The build problem (where dataflow scans go to die)

I want to be honest about this because it's where a lot of people get tripped up.

Compiled languages — C, C++, Java, C#, Go — require the tool to actually compile the code. That means invoking your build system: `make`, `cmake`, `gradle`, `maven`, `cargo`, `go build`, whatever your project uses.

Automated build detection scans the target directory for build configuration files and infers the build system:

- `pom.xml` → Maven
- `build.gradle` / `build.gradle.kts` → Gradle
- `Cargo.toml` → cargo
- `requirements.txt` / `setup.py` / `pyproject.toml` → pip (interpreted, no build needed)
- `Makefile` → make
- `CMakeLists.txt` → cmake
- `meson.build` → meson
- `configure.ac` / `autogen.sh` → autotools

For interpreted languages (Python, JavaScript, Ruby) the extraction phase is just parsing, so no build step is needed.

**In practice, the build step is where dataflow setups fail most often.** Missing dependencies, environment-specific toolchains, vendored libraries that need to be present, custom compiler wrappers, code generation steps that need to run first — all of these cause extraction failures. The output is a partial database, which translates into partial coverage. Any honest pipeline logs which targets extracted successfully so the operator knows whether a scan covered what they think it covered.

---

## A worked example: the SQL injection trace

Going back to the example from Post 1:

```python
@app.route('/user/<user_id>')
def get_user(user_id):
    db = sqlite3.connect(':memory:')
    cursor = db.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
```

A pattern matcher fires on this immediately — the string concatenation reaching `cursor.execute` is a textbook pattern. But a dataflow analyser gives you something more: a structured flow.

CodeQL's output for this finding includes:

- **Source location:** `get_user`, parameter `user_id` (from Flask route binding, which CodeQL knows is a taint source)
- **Sink location:** the `cursor.execute(query)` call
- **Intermediate nodes:** the assignment `query = "SELECT * FROM users WHERE id = " + user_id` showing concatenation propagates taint
- **Path conditions:** none in this case — the flow is unconditional

That structured flow is what feeds downstream LLM validation, if you have one. A downstream stage doesn't have to re-derive that `user_id` is attacker-controlled; the dataflow tool already proved it. The stage's job is to verify the flow against the actual source code, reason about exploitability, and produce a verdict.

---

## The path-condition problem (and a preview of the next post)

There's one nuance worth introducing here, because it sets up the next post exactly.

When a dataflow tool reports a flow that passes through one or more conditional branches, those branches impose constraints on the data. For example:

```c
void f(int x, char *buf) {
    if (x > 100) return;
    if (x >= 50) {
        if (x < 50) {
            strcpy(dead_buf, buf);   // tool flags this as a sink
        }
    }
}
```

A dataflow analyser correctly identifies a flow from `buf` to `strcpy`, because `buf` is potentially attacker-controlled and `strcpy` is dangerous. But the inner `if (x < 50)` is only reachable when `x >= 50` (from the outer branch) *and* `x < 50` (from the inner). Those conditions are mutually contradictory. The `strcpy` is dead code.

A naive pipeline would burn an expensive review — human or LLM — figuring this out. A smarter pipeline runs the path conditions through an SMT solver first. The solver returns "unsat" in microseconds. The finding is discarded before anyone wastes time on it.

That's the entire premise of the next post.

---

## For the AI/ML engineers reading this

A few things about dataflow analysis worth internalising if you're building LLM systems:

- **Structured output is gold.** A dataflow tool gives you a tree of locations and edges, not free text. That's straight-line LLM context — no parsing, no extraction prompt, no risk of the LLM misreading. If your pipeline can get structured output from upstream tools, take it.
- **Reasoning at the wrong layer is expensive.** Asking an LLM "is this code path reachable?" is asking it to do constraint solving. SMT solvers do constraint solving better and cheaper. Identify the parts of your problem that have deterministic solvers and use them; reserve the LLM for things that genuinely need fuzzy reasoning.
- **Build systems break.** If your pipeline depends on extracting build-dependent context, expect 10–30% of repositories to fail extraction in some way. Design for partial coverage gracefully; don't let one missing dependency abort the whole run.
- **Multi-source dedup is real work.** Once you have pattern matching + dataflow + fuzzer crashes, you'll have multiple alerts for the same underlying bug. The merge layer is where you keep your downstream stages from re-validating the same thing three times.

---

## Next in series

- [Post 4 — Z3 SMT Solvers](./04-z3-smt-solver-filtering.md). The post about constraint solving that explains the prettiest engineering trick in security analysis.

## Sources and further reading
- *[CodeQL documentation](https://codeql.github.com/docs/) — query language reference and tutorials*
- *[CodeQL Standard Libraries on GitHub](https://github.com/github/codeql) — the source/sink/sanitiser catalogues for every supported language*
- *Avgerinos et al., ["The Mayhem Cyber Reasoning System"](https://users.ece.cmu.edu/~dbrumley/pdf/Avgerinos%20et%20al._2018_The%20Mayhem%20Cyber%20Reasoning%20System.pdf) — IEEE S&P Magazine, 2018. The system that won DARPA's Cyber Grand Challenge in 2016; a good read on combining static analysis with symbolic execution in production.*
- *Cifuentes & Scholz, ["Parfait — Designing a Scalable Bug Checker"](https://dl.acm.org/doi/10.1145/1394504.1394505) — SAW 2008. One of the better short papers on the engineering trade-offs of dataflow-based bug finders.*
