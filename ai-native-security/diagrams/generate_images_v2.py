#!/usr/bin/env python3.12
"""Blog header / illustration images (v2) for the AI-Native Security Research series.

Run with Python 3.12. Outputs eight 1600x900 PNGs into the same directory as this file.
Each image is hand-tuned to the post it accompanies; the visual concepts differ from v1
so the two image sets are complementary rather than redundant.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# GitHub-dark palette
BG = "#0D1117"
PANEL = "#161B22"
PANEL2 = "#1C2129"
BORDER = "#30363D"
TEXT_PRI = "#E6EDF3"
TEXT_SEC = "#8B949E"
ACCENT_BLUE = "#58A6FF"
ACCENT_GREEN = "#56D364"
ACCENT_WARN = "#E3B341"
ACCENT_RED = "#F85149"
ACCENT_PURP = "#BC8CFF"
ACCENT_CYAN = "#39C5CF"

OUT_DIR = Path(__file__).parent
DPI = 150
FIG_SIZE = (16, 9)  # 1600x900 at dpi=100; with dpi=150 -> 2400x1350


def make_fig():
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=100)
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 90)
    ax.set_axis_off()
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    return fig, ax


def panel(ax, x, y, w, h, fc=PANEL, ec=BORDER, lw=1.2, radius=0.6, alpha=1.0):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={radius}",
        linewidth=lw, edgecolor=ec, facecolor=fc, alpha=alpha,
    )
    ax.add_patch(box)
    return box


def arrow(ax, x1, y1, x2, y2, color=ACCENT_BLUE, lw=1.6, style="-|>", mut=12, ls="-"):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=mut,
        color=color, linewidth=lw, linestyle=ls,
    )
    ax.add_patch(a)
    return a


def title(ax, text, sub=None, x=80, y=84):
    ax.text(x, y, text, color=TEXT_PRI, ha="center", va="center",
            fontsize=22, fontweight="bold", family="DejaVu Sans")
    if sub:
        ax.text(x, y - 4.2, sub, color=TEXT_SEC, ha="center", va="center",
                fontsize=11, family="DejaVu Sans")


def footer(ax, text, x=80, y=3):
    ax.text(x, y, text, color=TEXT_SEC, ha="center", va="center",
            fontsize=9.5, style="italic", family="DejaVu Sans")


def save(fig, name):
    out = OUT_DIR / name
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Post 1 — Four pillars feeding an AI validation core
# ---------------------------------------------------------------------------
def post1():
    fig, ax = make_fig()
    title(ax,
          "AI-Native Security Research",
          sub="Four pillars feed one AI validation core, not the other way round")

    # The central AI core
    cx, cy, cw, ch = 65, 36, 30, 20
    panel(ax, cx, cy, cw, ch, fc="#1F2632", ec=ACCENT_BLUE, lw=2.2, radius=1.2)
    ax.text(cx + cw / 2, cy + ch - 4.5, "AI VALIDATION", color=ACCENT_BLUE,
            ha="center", va="center", fontsize=14, fontweight="bold")
    ax.text(cx + cw / 2, cy + ch - 9, "8 staged LLM checks",
            color=TEXT_PRI, ha="center", va="center", fontsize=10.5)
    ax.text(cx + cw / 2, cy + ch - 13, "fresh-context verifiers", color=TEXT_SEC,
            ha="center", va="center", fontsize=9.5, style="italic")
    ax.text(cx + cw / 2, cy + 3, "Stages 0 → A B C D E F → 1", color=ACCENT_PURP,
            ha="center", va="center", fontsize=10, family="DejaVu Sans Mono")

    # Four pillar tiles around it
    pillars = [
        # x, y, w, h, color, title, subtitle
        (8,  60, 38, 17, ACCENT_GREEN, "Static pattern analysis",
         "Semgrep / AST rules\nseconds, every commit"),
        (113, 60, 38, 17, ACCENT_CYAN, "Dataflow analysis",
         "CodeQL / taint tracking\nminutes, needs build"),
        (8,  13, 38, 17, ACCENT_WARN, "Coverage-guided fuzzing",
         "AFL++ / libFuzzer\nhours, hard crashes"),
        (113, 13, 38, 17, ACCENT_PURP, "Dynamic web testing",
         "live endpoints\nconfig + auth bugs"),
    ]

    for x, y, w, h, color, t, s in pillars:
        panel(ax, x, y, w, h, fc=PANEL2, ec=color, lw=1.6, radius=0.9)
        ax.text(x + w / 2, y + h - 4, t, color=color, ha="center",
                va="center", fontsize=11.5, fontweight="bold")
        ax.text(x + w / 2, y + h - 11, s, color=TEXT_SEC, ha="center",
                va="center", fontsize=9.2)

    # Arrows from pillars into core
    arrow(ax, 46, 68, 65, 52, color=ACCENT_GREEN, lw=1.6)
    arrow(ax, 113, 68, 95, 52, color=ACCENT_CYAN, lw=1.6)
    arrow(ax, 46, 22, 65, 40, color=ACCENT_WARN, lw=1.6)
    arrow(ax, 113, 22, 95, 40, color=ACCENT_PURP, lw=1.6)

    # Output strip
    panel(ax, 50, 6, 60, 5, fc=PANEL, ec=BORDER, radius=0.6)
    ax.text(80, 8.5, "calibrated findings.json  +  validation-report.md",
            color=TEXT_PRI, ha="center", va="center",
            fontsize=10.5, family="DejaVu Sans Mono")
    arrow(ax, 80, 36, 80, 11.4, color=ACCENT_BLUE, lw=1.5)

    footer(ax, "Part 1 — every pillar sees a different part of the elephant; the AI layer reconciles them")
    save(fig, "01-ai-native-security.png")


# ---------------------------------------------------------------------------
# Post 2 — Regex vs AST pattern matching
# ---------------------------------------------------------------------------
def post2():
    fig, ax = make_fig()
    title(ax,
          "Why a Regex Isn't Enough",
          sub="Semgrep matches on the parsed shape of code, not the text")

    code_lines = [
        ("// regex: /eval\\(/", TEXT_SEC),
        ("eval(req.body.script)", ACCENT_RED),
        ("obj.eval(x)            // method call",   TEXT_PRI),
        ('msg = "calls eval("    // string literal', TEXT_PRI),
        ("var myEval = 1         // identifier",   TEXT_PRI),
        ("function eval(){}      // local fn",     TEXT_PRI),
    ]

    # LEFT panel — regex
    lx, ly, lw, lh = 6, 18, 70, 56
    panel(ax, lx, ly, lw, lh, fc=PANEL, ec=ACCENT_RED, lw=1.8, radius=0.9)
    ax.text(lx + lw / 2, ly + lh - 4, "grep / regex",
            color=ACCENT_RED, ha="center", va="center",
            fontsize=14, fontweight="bold")
    ax.text(lx + lw / 2, ly + lh - 8.5,
            "matches on raw bytes — five false positives below",
            color=TEXT_SEC, ha="center", va="center", fontsize=10)

    yy = ly + lh - 14
    for line, col in code_lines:
        ax.text(lx + 3, yy, line, color=col, ha="left", va="center",
                fontsize=10.5, family="DejaVu Sans Mono")
        if col == ACCENT_RED:
            ax.text(lx + lw - 4, yy, "TP",
                    color=ACCENT_RED, ha="right", va="center", fontsize=9.5,
                    fontweight="bold")
        else:
            ax.text(lx + lw - 4, yy, "FP",
                    color=ACCENT_WARN, ha="right", va="center", fontsize=9.5,
                    fontweight="bold")
        yy -= 5.6

    # RIGHT panel — AST
    rx, ry, rw, rh = 84, 18, 70, 56
    panel(ax, rx, ry, rw, rh, fc=PANEL, ec=ACCENT_GREEN, lw=1.8, radius=0.9)
    ax.text(rx + rw / 2, ry + rh - 4, "Semgrep (AST pattern)",
            color=ACCENT_GREEN, ha="center", va="center",
            fontsize=14, fontweight="bold")
    ax.text(rx + rw / 2, ry + rh - 8.5,
            "one true match, no comments, no method calls, no strings",
            color=TEXT_SEC, ha="center", va="center", fontsize=10)

    rule = (
        "rules:\n"
        "  - id: dangerous-eval\n"
        "    pattern: eval($CODE)\n"
        "    languages: [javascript]\n"
        "    message: 'Avoid eval()'\n"
        "    severity: WARNING"
    )
    ax.text(rx + 3, ry + rh - 16, rule, color=TEXT_PRI, ha="left", va="top",
            fontsize=10.5, family="DejaVu Sans Mono")

    panel(ax, rx + 3, ry + 6, rw - 6, 9, fc=PANEL2, ec=BORDER, radius=0.5)
    ax.text(rx + rw / 2, ry + 12.4, "Call(name='eval', args=[$CODE])",
            color=ACCENT_GREEN, ha="center", va="center",
            fontsize=10.5, family="DejaVu Sans Mono", fontweight="bold")
    ax.text(rx + rw / 2, ry + 8.4, "structured query over the parse tree",
            color=TEXT_SEC, ha="center", va="center",
            fontsize=9.5, style="italic")

    # Cross-tag in middle
    panel(ax, 75, 42, 10, 8, fc=PANEL2, ec=BORDER, radius=0.8)
    ax.text(80, 46, "vs", color=TEXT_PRI, ha="center", va="center",
            fontsize=13, fontweight="bold")

    footer(ax, "Part 2 — text-level matching can't tell code from comments; structure-level matching can")
    save(fig, "02-pattern-matching.png")


# ---------------------------------------------------------------------------
# Post 3 — Multi-function taint trace
# ---------------------------------------------------------------------------
def post3():
    fig, ax = make_fig()
    title(ax,
          "Dataflow Analysis: Bugs Across Function Boundaries",
          sub="Every line looks fine on its own — the bug is the composition")

    # Four boxes in a row, taint flowing left → right
    nodes = [
        ("SOURCE",   "request.args.get('name')",  "Flask route",   ACCENT_RED,   6),
        ("HELPER",   "render_user(name)",         "no escape",     ACCENT_WARN, 43),
        ("HELPER",   "f\"<h1>{s}</h1>\"",         "taint propagates", ACCENT_WARN, 80),
        ("SINK",     "Response(html,\n  mimetype='text/html')", "XSS — html injected", ACCENT_RED, 117),
    ]

    nw, nh, ny = 35, 26, 38
    for label, code, note, color, x in nodes:
        panel(ax, x, ny, nw, nh, fc=PANEL, ec=color, lw=1.8, radius=0.8)
        ax.text(x + nw / 2, ny + nh - 4.5, label,
                color=color, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(x + nw / 2, ny + nh - 12, code,
                color=TEXT_PRI, ha="center", va="center",
                fontsize=10.2, family="DejaVu Sans Mono")
        ax.text(x + nw / 2, ny + 4, note,
                color=TEXT_SEC, ha="center", va="center",
                fontsize=9.5, style="italic")

    # Arrows between nodes, labelled "tainted"
    for x_from, x_to in [(41, 43), (78, 80), (115, 117)]:
        arrow(ax, x_from, ny + nh / 2, x_to, ny + nh / 2,
              color=ACCENT_RED, lw=2.0, mut=14)
    for xm in [42, 79, 116]:
        ax.text(xm, ny + nh / 2 + 3.5, "tainted",
                color=ACCENT_RED, ha="center", va="center",
                fontsize=9, family="DejaVu Sans Mono", fontweight="bold")

    # Missing sanitiser banner along the chain
    panel(ax, 36, 22, 87, 8, fc="#2A1A1F", ec=ACCENT_WARN, lw=1.4, radius=0.6)
    ax.text(79.5, 26, "no sanitiser anywhere on this path",
            color=ACCENT_WARN, ha="center", va="center",
            fontsize=11, fontweight="bold")

    # Pattern matcher vs dataflow comparison strip
    panel(ax, 6, 68, 60, 10, fc=PANEL2, ec=ACCENT_RED, lw=1.4, radius=0.6)
    ax.text(9, 75.5, "Pattern matcher", color=ACCENT_RED, fontsize=10.5,
            fontweight="bold", ha="left", va="center")
    ax.text(9, 71, "sees one function — fires nothing",
            color=TEXT_SEC, fontsize=10, ha="left", va="center")

    panel(ax, 94, 68, 60, 10, fc=PANEL2, ec=ACCENT_GREEN, lw=1.4, radius=0.6)
    ax.text(97, 75.5, "Dataflow analyser (CodeQL)",
            color=ACCENT_GREEN, fontsize=10.5,
            fontweight="bold", ha="left", va="center")
    ax.text(97, 71, "follows the chain across files — fires once",
            color=TEXT_SEC, fontsize=10, ha="left", va="center")

    # Bottom callout
    panel(ax, 30, 7, 100, 8, fc=PANEL, ec=BORDER, radius=0.6)
    ax.text(80, 11.2, "source  →  helper  →  helper  →  sink",
            color=TEXT_PRI, ha="center", va="center",
            fontsize=11, family="DejaVu Sans Mono")

    footer(ax, "Part 3 — pattern matchers are intra-procedural by design; this XSS spans three functions")
    save(fig, "03-dataflow-analysis.png")


# ---------------------------------------------------------------------------
# Post 4 — Z3 SAT / UNSAT / Indeterminate trichotomy
# ---------------------------------------------------------------------------
def post4():
    fig, ax = make_fig()
    title(ax,
          "Z3 Pre-Filters Dataflow Findings",
          sub="Three verdicts on the path conditions — only SAT continues")

    # Three columns
    cols = [
        ("SAT",
         "real bug — keep",
         ACCENT_RED,
         "uint32_t n = read_u32();\n"
         "uint32_t bytes = n * 16;\n"
         "char *buf = malloc(bytes);\n"
         "for (i=0;i<n;i++)\n"
         "    memcpy(&buf[i*16], ..);",
         "witness:\nn = 0x10000001\nbytes = 0x00000010\n→ heap overflow",
         "Send to LLM with\nconcrete PoC values"),
        ("UNSAT",
         "false positive — drop",
         ACCENT_GREEN,
         "if (x > 100) return;\n"
         "if (x >= 50) {\n"
         "    if (x < 50) {\n"
         "        strcpy(dst, buf);\n"
         "    }\n"
         "}",
         "x >= 50 AND x < 50\n→ unsatisfiable\n→ dead code",
         "Discarded — LLM\nnever sees it"),
        ("INDETERMINATE",
         "decide via LLM",
         ACCENT_WARN,
         "if (validate(input)\n"
         "    && input.len > 0) {\n"
         "    process(input);\n"
         "}",
         "validate() is opaque\nto the SMT theory\n→ no verdict",
         "Send to LLM\nwithout pre-filter"),
    ]

    cw, ch, cy = 47, 64, 12
    xs = [6, 56.5, 107]
    for (verdict, sub, color, code, witness, action), x in zip(cols, xs):
        panel(ax, x, cy, cw, ch, fc=PANEL, ec=color, lw=2.0, radius=0.9)
        # Header
        ax.text(x + cw / 2, cy + ch - 5, verdict,
                color=color, ha="center", va="center",
                fontsize=14, fontweight="bold")
        ax.text(x + cw / 2, cy + ch - 9.5, sub,
                color=TEXT_SEC, ha="center", va="center",
                fontsize=10.5, style="italic")

        # Code block
        panel(ax, x + 2.5, cy + ch - 33, cw - 5, 21,
              fc=PANEL2, ec=BORDER, radius=0.5)
        ax.text(x + 4.5, cy + ch - 14.5, code,
                color=TEXT_PRI, ha="left", va="top",
                fontsize=9.6, family="DejaVu Sans Mono")

        # Z3 verdict box
        panel(ax, x + 2.5, cy + ch - 49, cw - 5, 14,
              fc="#181C24", ec=color, lw=1.1, radius=0.5)
        ax.text(x + 4.5, cy + ch - 37, witness,
                color=color, ha="left", va="top",
                fontsize=9.4, family="DejaVu Sans Mono")

        # Action
        panel(ax, x + 2.5, cy + 2, cw - 5, 8,
              fc=PANEL2, ec=BORDER, radius=0.5)
        ax.text(x + cw / 2, cy + 6, action,
                color=TEXT_PRI, ha="center", va="center", fontsize=9.5)

    footer(ax, "Part 4 — bitvector arithmetic in microseconds; cheaper than every LLM token it saves")
    save(fig, "04-smt-solver.png")


# ---------------------------------------------------------------------------
# Post 5 — AFL coverage-guided fuzzing loop
# ---------------------------------------------------------------------------
def post5():
    fig, ax = make_fig()
    title(ax,
          "Coverage-Guided Fuzzing (AFL++)",
          sub="The feedback loop that learns the program's shape from crashes alone")

    # Five circular-ish stations around a loop
    stations = [
        ("CORPUS",          "seed inputs",                ACCENT_BLUE,  18, 60),
        ("MUTATOR",         "bit-flips, splices,\nhavoc", ACCENT_PURP,  56, 70),
        ("INSTRUMENTED\nTARGET",  "afl-clang-fast\nedge counters",ACCENT_CYAN, 104, 70),
        ("COVERAGE MAP",    "edge -> hit count\n(shared mem)", ACCENT_WARN, 134, 40),
        ("TRIAGE",          "crashes/ + ASAN\ndedup by stack", ACCENT_RED,  84, 24),
    ]

    sw, sh = 28, 16
    centers = []
    for name, sub, color, cx, cy in stations:
        panel(ax, cx - sw / 2, cy - sh / 2, sw, sh,
              fc=PANEL, ec=color, lw=1.8, radius=1.0)
        ax.text(cx, cy + 3, name, color=color, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(cx, cy - 3, sub, color=TEXT_SEC, ha="center", va="center",
                fontsize=9.2)
        centers.append((cx, cy))

    # Arrows around the loop
    loop_edges = [
        (centers[0], centers[1], "pull input"),
        (centers[1], centers[2], "mutated bytes"),
        (centers[2], centers[3], "edges hit"),
        (centers[3], centers[0], "new edge?\nkeep input", True),
        (centers[3], centers[4], "crash"),
    ]
    for i, edge in enumerate(loop_edges):
        if len(edge) == 4:
            (x1, y1), (x2, y2), label, _ = edge
            color = ACCENT_GREEN
        else:
            (x1, y1), (x2, y2), label = edge
            color = ACCENT_BLUE
        # shrink endpoints
        dx, dy = x2 - x1, y2 - y1
        d = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / d, dy / d
        ox, oy = uy * 0.0, -ux * 0.0
        arrow(ax,
              x1 + ux * 14 + ox, y1 + uy * 8 + oy,
              x2 - ux * 14 + ox, y2 - uy * 8 + oy,
              color=color, lw=1.6, mut=14)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, label, color=TEXT_PRI, ha="center", va="center",
                fontsize=9, family="DejaVu Sans Mono",
                bbox=dict(boxstyle="round,pad=0.25", fc=BG, ec=BORDER, lw=0.6))

    # RAPTOR additions sidebar
    panel(ax, 4, 4, 152, 9, fc=PANEL2, ec=ACCENT_PURP, lw=1.4, radius=0.5)
    ax.text(8, 8.5,
            "RAPTOR adds:  target detection  •  harness scaffolding  •  afl-cmin corpus mgmt  "
            "•  master/secondary parallel  •  ASAN/UBSAN/MSAN triage  •  GDB stack dedup",
            color=TEXT_PRI, ha="left", va="center",
            fontsize=10, family="DejaVu Sans Mono")

    footer(ax, "Part 5 — every input that hits a new edge stays in the queue; everything else is discarded")
    save(fig, "05-afl-fuzzing.png")


# ---------------------------------------------------------------------------
# Post 6 — Exploit feasibility: four verdicts
# ---------------------------------------------------------------------------
def post6():
    fig, ax = make_fig()
    title(ax,
          "Binary Exploit Feasibility (Stage E)",
          sub="Mechanical checks → one of four honest verdicts")

    # Top: checks pipeline (left to right)
    checks = [
        ("Mitigations",     "NX • PIE • RELRO\ncanaries"),
        ("ROP gadgets",     "count + quality\nbad-byte filter"),
        ("libc fingerprint","empirical probe\nnot version string"),
        ("One-gadget + Z3", "satisfy reg/mem\nconstraints"),
        ("Bad bytes",       "addr ∩ stripchars\n= ∅ ?"),
        ("Write targets",   "GOT • __free_hook\n_IO_FILE vtables"),
    ]
    bw, bh, by = 23.5, 14, 64
    bxs = [3, 28, 53, 78, 103, 128]
    for (t, s), x in zip(checks, bxs):
        panel(ax, x, by, bw, bh, fc=PANEL, ec=ACCENT_CYAN, lw=1.4, radius=0.7)
        ax.text(x + bw / 2, by + bh - 4, t,
                color=ACCENT_CYAN, ha="center", va="center",
                fontsize=10.5, fontweight="bold")
        ax.text(x + bw / 2, by + bh - 9.5, s,
                color=TEXT_SEC, ha="center", va="center", fontsize=9)
    for x_from, x_to in zip(bxs[:-1], bxs[1:]):
        arrow(ax, x_from + bw, by + bh / 2, x_to, by + bh / 2,
              color=BORDER, lw=1.2, mut=10)

    # Funnel: arrow into a synthesis bar, then fan out to all four verdicts
    arrow(ax, 80, 63, 80, 55, color=ACCENT_BLUE, lw=2.0, mut=14)
    panel(ax, 30, 48, 100, 7, fc=PANEL2, ec=ACCENT_BLUE, lw=1.4, radius=0.5)
    ax.text(80, 51.5, "LLM synthesises verdict from mechanical evidence",
            color=ACCENT_BLUE, ha="center", va="center",
            fontsize=10.5, fontweight="bold", style="italic")
    for verdict_x in [21, 59, 97, 135]:
        arrow(ax, 80, 48, verdict_x, 46.5, color=BORDER, lw=1.0, mut=10)

    # Bottom: four verdicts
    verdicts = [
        ("Likely exploitable",     "exploitable",
         "primitives exist,\nmitigations don't block",   ACCENT_RED),
        ("Difficult",              "confirmed_constrained",
         "primitives exist but\nchaining is non-trivial", ACCENT_WARN),
        ("Unlikely",               "confirmed_blocked",
         "known paths blocked\nby mitigations",          ACCENT_GREEN),
        ("Not applicable",         "—",
         "non-memory-corruption,\nuse Stage D verdict",  TEXT_SEC),
    ]
    vw, vh, vy = 36, 34, 12
    vxs = [3, 41, 79, 117]
    for (heading, status, body, color), x in zip(verdicts, vxs):
        panel(ax, x, vy, vw, vh, fc=PANEL, ec=color, lw=1.8, radius=0.9)
        ax.text(x + vw / 2, vy + vh - 5, heading,
                color=color, ha="center", va="center",
                fontsize=12.5, fontweight="bold")
        panel(ax, x + 3, vy + vh - 16, vw - 6, 7,
              fc=PANEL2, ec=BORDER, radius=0.4)
        ax.text(x + vw / 2, vy + vh - 12.5, status,
                color=TEXT_PRI, ha="center", va="center",
                fontsize=10.5, family="DejaVu Sans Mono")
        ax.text(x + vw / 2, vy + 6, body,
                color=TEXT_SEC, ha="center", va="center", fontsize=9.5)

    footer(ax, "Part 6 — a crash is the start of the work; the verdicts say what's actually shippable")
    save(fig, "06-exploit-feasibility.png")


# ---------------------------------------------------------------------------
# Post 7 — Generator vs verifier lanes
# ---------------------------------------------------------------------------
def post7():
    fig, ax = make_fig()
    title(ax,
          "The Fresh-Context Verifier Pattern",
          sub="Stages C and F run in separate sessions — they see claims, not reasoning")

    # Two lanes
    panel(ax, 4, 36, 152, 38, fc="#141925", ec=BORDER, lw=1.0, radius=0.8, alpha=0.6)
    panel(ax, 4, 12, 152, 20, fc="#1A1416", ec=BORDER, lw=1.0, radius=0.8, alpha=0.6)
    ax.text(7, 73, "GENERATOR LANE",
            color=ACCENT_BLUE, ha="left", va="top",
            fontsize=11.5, fontweight="bold", family="DejaVu Sans Mono")
    ax.text(7, 32, "VERIFIER LANE  (fresh context, no history)",
            color=ACCENT_RED, ha="left", va="top",
            fontsize=11.5, fontweight="bold", family="DejaVu Sans Mono")

    # Generator stages: 0, A, B, D, E, 1
    gen_stages = [
        ("0",  "Inventory",            "mechanical",   ACCENT_GREEN),
        ("A",  "Quick triage",         "LLM",          ACCENT_BLUE),
        ("B",  "Attack-path analysis", "LLM",          ACCENT_BLUE),
        ("D",  "Ruling + CVSS",        "LLM",          ACCENT_BLUE),
        ("E",  "Bin feasibility",      "if binary",    ACCENT_PURP),
        ("1",  "Report",               "mechanical",   ACCENT_GREEN),
    ]
    gw, gh, gy = 21, 22, 44
    gxs = [10, 35, 60, 85, 110, 135]
    for (sid, title_, sub, color), x in zip(gen_stages, gxs):
        panel(ax, x, gy, gw, gh, fc=PANEL, ec=color, lw=1.6, radius=0.7)
        ax.text(x + 4, gy + gh - 5, sid,
                color=color, ha="center", va="center",
                fontsize=16, fontweight="bold")
        ax.text(x + gw / 2 + 2, gy + gh - 7, title_,
                color=TEXT_PRI, ha="center", va="center",
                fontsize=10, fontweight="bold")
        ax.text(x + gw / 2, gy + gh - 13, sub,
                color=TEXT_SEC, ha="center", va="center", fontsize=9, style="italic")
    # Arrows along generator
    for x_from, x_to in zip(gxs[:-1], gxs[1:]):
        arrow(ax, x_from + gw, gy + gh / 2, x_to, gy + gh / 2,
              color=BORDER, lw=1.4, mut=12)

    # Verifier stages: C and F
    ver_stages = [
        ("C",  "Verify B's claims\nagainst source",         60),
        ("F",  "Cross-stage\nconsistency",                 110),
    ]
    vw, vh, vy = 21, 16, 14
    for sid, t, x in ver_stages:
        panel(ax, x, vy, vw, vh, fc=PANEL, ec=ACCENT_RED, lw=1.6, radius=0.7)
        ax.text(x + 4, vy + vh - 4, sid,
                color=ACCENT_RED, ha="center", va="center",
                fontsize=15, fontweight="bold")
        ax.text(x + vw / 2 + 2, vy + vh - 9, t,
                color=TEXT_PRI, ha="center", va="center", fontsize=9.5)

    # Dashed claim arrows (down) and correction arrows (up)
    # B (gxs[2]) -> C (x=60); D->F? F covers all outputs so F arrow comes from D/E
    arrow(ax, 60 + gw / 2, gy, 60 + vw / 2, vy + vh,
          color=ACCENT_RED, lw=1.3, ls=(0, (4, 3)), mut=12)
    arrow(ax, 60 + vw / 2 + 2, vy + vh, 60 + gw / 2 + 2, gy,
          color=ACCENT_GREEN, lw=1.1, ls=(0, (2, 2)), mut=10)
    ax.text(82, 32.5, "claims ↓ / corrections ↑",
            color=TEXT_SEC, ha="left", va="center", fontsize=9, style="italic")

    arrow(ax, 110 + gw / 2, gy, 110 + vw / 2, vy + vh,
          color=ACCENT_RED, lw=1.3, ls=(0, (4, 3)), mut=12)
    arrow(ax, 110 + vw / 2 + 2, vy + vh, 110 + gw / 2 + 2, gy,
          color=ACCENT_GREEN, lw=1.1, ls=(0, (2, 2)), mut=10)

    # Bottom rationale strip
    panel(ax, 4, 3, 152, 6, fc=PANEL2, ec=BORDER, radius=0.5)
    ax.text(80, 6.1,
            "asking the same model in the same context to 'double-check' invites sycophancy and anchoring; "
            "a fresh context with only the claim + source does not",
            color=TEXT_PRI, ha="center", va="center",
            fontsize=10, style="italic")

    footer(ax, "Part 7 — the single most generalisable LLM-architecture pattern in the series", y=0.6)
    save(fig, "07-llm-validation-pipeline.png")


# ---------------------------------------------------------------------------
# Post 8 — The /agentic orchestration command
# ---------------------------------------------------------------------------
def post8():
    fig, ax = make_fig()
    title(ax,
          "/agentic — One Command, Full Pipeline",
          sub="Parallel scanners → dedup → 8 LLM stages → calibrated report")

    # Command bar (below the subtitle so the two don't overlap)
    panel(ax, 18, 70, 124, 5.5, fc=PANEL2, ec=ACCENT_PURP, lw=1.5, radius=0.5)
    ax.text(80, 72.75, "$ raptor /agentic ./target  --budget 5.00  [--consensus]  [--judge]  [--exploit]  [--patch]",
            color=TEXT_PRI, ha="center", va="center",
            fontsize=10.5, family="DejaVu Sans Mono")

    # Row 1: parallel scanners
    scanners = [
        ("Semgrep",   ACCENT_GREEN, 5),
        ("CodeQL",    ACCENT_CYAN,  31),
        ("AFL++",     ACCENT_WARN,  57),
        ("SCA / OSV", ACCENT_BLUE,  83),
        ("Web (alpha)", ACCENT_PURP, 109),
        ("Z3 pre-filter", ACCENT_RED, 135),
    ]
    sw, sh, sy = 20, 10, 58
    for name, color, x in scanners:
        panel(ax, x, sy, sw, sh, fc=PANEL, ec=color, lw=1.4, radius=0.6)
        ax.text(x + sw / 2, sy + sh / 2, name,
                color=color, ha="center", va="center",
                fontsize=10.5, fontweight="bold")

    # Row 2: merge / dedup
    panel(ax, 30, 44, 100, 8, fc=PANEL, ec=ACCENT_BLUE, lw=1.6, radius=0.6)
    ax.text(80, 48, "SARIF merge  +  CWE-aware dedup  +  inventory",
            color=ACCENT_BLUE, ha="center", va="center",
            fontsize=11, fontweight="bold")
    for x in [15, 41, 67, 93, 119, 145]:
        arrow(ax, x, sy, 80, 52, color=BORDER, lw=0.9, mut=8)

    # Row 3: 8 LLM stages
    stages = [
        ("0", ACCENT_GREEN),
        ("A", ACCENT_BLUE),
        ("B", ACCENT_BLUE),
        ("C", ACCENT_RED),
        ("D", ACCENT_BLUE),
        ("E", ACCENT_PURP),
        ("F", ACCENT_RED),
        ("1", ACCENT_GREEN),
    ]
    tw, th, ty = 12, 10, 28
    txs = [10 + i * 17.5 for i in range(8)]
    arrow(ax, 80, 44, 80, ty + th, color=ACCENT_BLUE, lw=1.4)
    for (sid, color), x in zip(stages, txs):
        panel(ax, x, ty, tw, th, fc=PANEL, ec=color, lw=1.6, radius=0.5)
        ax.text(x + tw / 2, ty + th / 2 + 0.3, sid,
                color=color, ha="center", va="center",
                fontsize=14, fontweight="bold")
    for x_from, x_to in zip(txs[:-1], txs[1:]):
        arrow(ax, x_from + tw, ty + th / 2, x_to, ty + th / 2,
              color=BORDER, lw=1.0, mut=10)

    # Stage labels under
    labels = ["inventory", "triage", "attack path", "verify", "rule + CVSS",
              "feasibility", "consistency", "report"]
    for label, x in zip(labels, txs):
        ax.text(x + tw / 2, ty - 2, label,
                color=TEXT_SEC, ha="center", va="top",
                fontsize=8.5, family="DejaVu Sans Mono")

    # Row 4: outputs (5 boxes, even gaps, fit within 0..160 canvas)
    outs = [
        ("findings.json",          ACCENT_GREEN, 4),
        ("validation-report.md",   ACCENT_GREEN, 35),
        ("diagrams.md",            ACCENT_CYAN,  66),
        ("annotations/*.md",       ACCENT_PURP,  97),
        ("cost-tracker.json",      ACCENT_WARN, 128),
    ]
    ow, oh, oy = 28, 8, 11
    for name, color, x in outs:
        panel(ax, x, oy, ow, oh, fc=PANEL2, ec=color, lw=1.2, radius=0.5)
        ax.text(x + ow / 2, oy + oh / 2, name,
                color=TEXT_PRI, ha="center", va="center",
                fontsize=9.5, family="DejaVu Sans Mono")
    arrow(ax, 80, ty, 80, oy + oh, color=ACCENT_BLUE, lw=1.4)

    footer(ax, "Part 8 — every stage is gated; --budget stops gracefully rather than truncating silently",
           y=4.5)
    save(fig, "08-putting-together.png")


# ---------------------------------------------------------------------------
def main():
    print(f"Generating v2 blog images → {OUT_DIR}")
    post1()
    post2()
    post3()
    post4()
    post5()
    post6()
    post7()
    post8()
    print("done.")


if __name__ == "__main__":
    main()
