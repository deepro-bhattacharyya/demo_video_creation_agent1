#!/usr/bin/env python3
"""Generate docs/architecture.png — DemoVideoBot pipeline flow diagram.

Clean, light-background flowchart intended for presentations / POC walkthroughs.

Run from the project root:
    python scripts/generate_architecture_png.py
"""

import os
import sys

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Polygon
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:
    print("matplotlib/numpy not found.  Install:  pip install matplotlib")
    sys.exit(1)

# ── Palette (light theme) ─────────────────────────────────────────────────────
PAGE     = "#ffffff"
INK      = "#1f2937"     # near-black text
MUTED    = "#6b7280"     # gray annotations
DET_FILL = "#dfe5ee"     # deterministic step
DET_EDGE = "#9aa7bd"
LLM_FILL = "#ede9fe"     # LLM step
LLM_EDGE = "#c4b5fd"
LLM_BADGE = "#7c3aed"
DEC_FILL = "#fde9b5"     # decision diamond
DEC_EDGE = "#e0a92e"
HUM_FILL = "#ffe0c2"     # human review
HUM_EDGE = "#f0a45f"
SE_FILL  = "#ccf5ec"     # side-effect / terminal
SE_EDGE  = "#5fc9b5"
END_FILL = "#2d3748"     # start / end
BOX_LINE = "#cbd3e1"
TITLE_A  = "#1e3a8a"
TITLE_B  = "#3b82f6"

W, H, DPI = 20, 21, 150
fig, ax = plt.subplots(figsize=(W, H), dpi=DPI)
ax.set_xlim(0, W); ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor(PAGE)
ax.set_facecolor(PAGE)


# ── Primitives ────────────────────────────────────────────────────────────────

def rbox(x, y, w, h, fill, edge, label, sub="", fs=13, sub_fs=10,
         tc=INK, lw=1.6, z=4, radius=0.14, badge=None):
    ax.add_patch(FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=fill, edgecolor=edge, linewidth=lw, zorder=z,
    ))
    if sub:
        ax.text(x, y + 0.16, label, ha="center", va="center",
                fontsize=fs, color=tc, fontweight="bold", zorder=z+1)
        ax.text(x, y - 0.20, sub, ha="center", va="center",
                fontsize=sub_fs, color=MUTED, zorder=z+1)
    else:
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fs, color=tc, fontweight="bold", zorder=z+1)
    if badge:
        bx, by = x + w/2 - 0.42, y + h/2 - 0.02
        ax.add_patch(FancyBboxPatch(
            (bx - 0.30, by - 0.16), 0.60, 0.32,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=LLM_BADGE, edgecolor="none", zorder=z+2))
        ax.text(bx, by, badge, ha="center", va="center",
                fontsize=8, color="white", fontweight="bold", zorder=z+3)


def diamond(x, y, w, h, label, sub="", fs=12, sub_fs=9, z=4):
    pts = [(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=DEC_FILL,
                         edgecolor=DEC_EDGE, linewidth=1.6, zorder=z))
    if sub:
        ax.text(x, y + 0.16, label, ha="center", va="center",
                fontsize=fs, color=INK, fontweight="bold", zorder=z+1)
        ax.text(x, y - 0.20, sub, ha="center", va="center",
                fontsize=sub_fs, color=MUTED, zorder=z+1)
    else:
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fs, color=INK, fontweight="bold", zorder=z+1)


def pill(x, y, w, h, label, z=4):
    ax.add_patch(FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={h/2}",
        facecolor=END_FILL, edgecolor="none", zorder=z))
    ax.text(x, y, label, ha="center", va="center",
            fontsize=13, color="white", fontweight="bold", zorder=z+1)


def arr(x1, y1, x2, y2, color="#7b8494", lw=1.7, rad=None, label=None,
        lx=None, ly=None, lfs=9.5, lcolor=INK, lweight="bold"):
    kw = dict(arrowstyle="-|>,head_width=0.35,head_length=0.6",
              color=color, lw=lw, shrinkA=6, shrinkB=6)
    if rad:
        kw["connectionstyle"] = f"arc3,rad={rad}"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=kw, zorder=3)
    if label:
        ax.text(lx if lx is not None else (x1+x2)/2,
                ly if ly is not None else (y1+y2)/2,
                label, ha="center", va="center", fontsize=lfs,
                color=lcolor, fontweight=lweight, zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", fc=PAGE, ec="none"))


def sidenote(x, y, txt, to_x, to_y, fs=10):
    ax.annotate("", xy=(to_x, to_y), xytext=(x + 0.05, y),
                arrowprops=dict(arrowstyle="-", color="#c2c8d2",
                                lw=1.2, linestyle=(0, (3, 3))), zorder=2)
    ax.text(x, y, txt, ha="left", va="center", fontsize=fs,
            color=MUTED, style="italic", zorder=6)


def panel(x0, y0, x1, y1, z=3):
    ax.add_patch(FancyBboxPatch(
        (x0, y0), x1-x0, y1-y0,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        facecolor="#fbfcfe", edgecolor=BOX_LINE, linewidth=1.4, zorder=z))


# ─────────────────────────────────────────────────────────────────────────────
# Title bar (blue gradient)
# ─────────────────────────────────────────────────────────────────────────────
cmap = LinearSegmentedColormap.from_list("t", [TITLE_A, TITLE_B])
grad = np.linspace(0, 1, 256).reshape(1, -1)
ax.imshow(grad, extent=[0, W, 19.35, 21.0], aspect="auto", cmap=cmap, zorder=2)
ax.text(0.7, 20.4, "DemoVideoBot — Pipeline & Video Flow",
        ha="left", va="center", fontsize=25, color="white",
        fontweight="bold", zorder=5)
ax.text(0.72, 19.75,
        "Automated demo-video generator  ·  LangGraph state machine  ·  "
        "narrated + silent cut per agent",
        ha="left", va="center", fontsize=12, color="#dbe4ff", zorder=5)

# ─────────────────────────────────────────────────────────────────────────────
# Footer bar
# ─────────────────────────────────────────────────────────────────────────────
ax.add_patch(plt.Rectangle((0, 0), W, 0.85, facecolor=END_FILL, zorder=2))
ax.text(W/2, 0.55,
        "LangGraph · Gemini 2.0 Flash · Edge TTS · Playwright · FFmpeg · "
        "FastAPI · React + Vite",
        ha="center", va="center", fontsize=12.5, color="white",
        fontweight="bold", zorder=5)
ax.text(W/2, 0.25,
        "Two input modes: AgenticQEAHub platform  or  local standalone folder  ·  "
        "runs behind corporate TLS proxy (truststore)",
        ha="center", va="center", fontsize=9.5, color="#aab4c5", zorder=5)


# ─────────────────────────────────────────────────────────────────────────────
# Main flow column
# ─────────────────────────────────────────────────────────────────────────────
cx = 6.9
NW, NH = 3.7, 0.95

pill(cx, 18.35, 1.9, 0.62, "START")

diamond(cx, 17.15, 2.5, 1.15, "Input source?", "")

# Two input mode boxes
hub_x, sta_x = 4.15, 9.65
rbox(hub_x, 15.75, 3.5, 0.95, DET_FILL, DET_EDGE,
     "Platform (Hub)", "login → navigate → run", fs=12, sub_fs=9)
rbox(sta_x, 15.75, 3.7, 0.95, DET_FILL, DET_EDGE,
     "Standalone folder", "demo_config.yaml → subprocess", fs=12, sub_fs=9)

arr(cx, 17.15 - 0.58, cx, 17.15 - 0.58)  # noop guard
# START -> diamond
arr(cx, 18.05, cx, 17.73)
# diamond -> hub / standalone
arr(cx - 0.9, 17.0, hub_x, 16.25, rad=-0.15, label="HUB",
    lx=4.9, ly=16.85, lfs=9)
arr(cx + 0.9, 17.0, sta_x, 16.25, rad=0.15, label="STANDALONE",
    lx=9.1, ly=16.85, lfs=9)

# Pipeline nodes
NODES = [
    (14.30, DET_FILL, DET_EDGE, "1  select_agent",
     "fetch agent name + spec", None),
    (12.85, SE_FILL,  SE_EDGE,  "2  capture_run",
     "run agent · screen-record  (×2 retry)", None),
    (11.40, LLM_FILL, LLM_EDGE, "3  generate_script",
     "run transcript → timed scenes  (×3 retry)", "LLM"),
]
for (ny, fill, edge, lbl, sub, badge) in NODES:
    rbox(cx, ny, NW, NH, fill, edge, lbl, sub, badge=badge)

# input boxes -> select_agent
arr(hub_x, 15.27, cx - 0.7, 14.78, rad=0.12)
arr(sta_x, 15.27, cx + 0.7, 14.78, rad=-0.12)
# select -> capture -> generate
arr(cx, 14.30 - NH/2, cx, 12.85 + NH/2)
arr(cx, 12.85 - NH/2, cx, 11.40 + NH/2)

# Human review
rbox(cx, 9.85, NW + 0.3, 1.0, HUM_FILL, HUM_EDGE,
     "4  review_script   [ || ]",
     "human pause — approve or edit narration", fs=12.5, sub_fs=9.5)
arr(cx, 11.40 - NH/2, cx, 9.85 + 0.5)

# Fork
syn_x, sil_x = 4.55, 9.25
fork_y = 9.85 - 0.5
rbox(syn_x, 8.15, 3.5, 0.95, SE_FILL, SE_EDGE,
     "5  synthesize_audio", "Edge TTS → WAV track", fs=11.5, sub_fs=9)
rbox(sil_x, 8.15, 3.6, 0.95, SE_FILL, SE_EDGE,
     "6  assemble_silent", "FFmpeg captions cut", fs=11.5, sub_fs=9)
rbox(syn_x, 6.75, 3.5, 0.95, SE_FILL, SE_EDGE,
     "7  assemble_full", "recording + audio", fs=11.5, sub_fs=9)

arr(cx, fork_y, syn_x, 8.65, rad=0.2, label="APPROVE",
    lx=cx - 0.15, ly=9.05, lfs=9)
arr(cx, fork_y, sil_x, 8.65, rad=-0.2)
arr(syn_x, 8.15 - 0.48, syn_x, 6.75 + 0.48)

# finalize
rbox(cx, 5.30, NW + 0.2, 0.95, SE_FILL, SE_EDGE,
     "8  finalize", "ffprobe validate · clean up · write output/",
     fs=12.5, sub_fs=9.5)
arr(syn_x, 6.75 - 0.48, cx - 0.6, 5.78, rad=-0.15)
arr(sil_x, 8.15 - 0.48, cx + 0.7, 5.78, rad=0.28)

# END + output
pill(cx, 4.05, 1.9, 0.62, "END")
arr(cx, 5.30 - 0.48, cx, 4.37)
rbox(cx, 2.85, NW + 1.0, 0.95, SE_FILL, SE_EDGE,
     "output/",
     "narrated_<agent>.mp4    ·    silent_<agent>.mp4",
     fs=12.5, sub_fs=10)
arr(cx, 3.74, cx, 3.33)


# ─────────────────────────────────────────────────────────────────────────────
# Left-side annotations
# ─────────────────────────────────────────────────────────────────────────────
sidenote(0.55, 16.7,
         "Hub logs into the platform;\nStandalone reads a local folder.",
         2.9, 17.15)
sidenote(0.55, 12.85,
         "Playwright records the browser;\nFFmpeg records the desktop\n"
         "for terminal agents.",
         cx - NW/2, 12.85)
sidenote(0.55, 11.40,
         "Gemini reads the run transcript\nand writes the narration —\n"
         "one LLM call per run.",
         cx - NW/2, 11.40)
sidenote(0.55, 9.85,
         "Pipeline pauses so a human can\nedit lines before anything renders.",
         cx - (NW+0.3)/2, 9.85)
sidenote(0.55, 7.45,
         "Narrated and silent cuts\nare built in parallel.",
         syn_x - 3.5/2, 7.45)


# ─────────────────────────────────────────────────────────────────────────────
# Legend (top-right)
# ─────────────────────────────────────────────────────────────────────────────
lx0, ly1 = 13.6, 18.55
panel(lx0, 15.15, 19.6, ly1)
ax.text(lx0 + 0.35, ly1 - 0.35, "Legend", fontsize=13,
        color=INK, fontweight="bold", zorder=6)

legend = [
    (DET_FILL, DET_EDGE, "square", "Deterministic step (no LLM)"),
    (LLM_FILL, LLM_EDGE, "square", "LLM step (Gemini)"),
    (DEC_FILL, DEC_EDGE, "diamond", "Decision / routing"),
    (HUM_FILL, HUM_EDGE, "square", "Human review (pause)"),
    (SE_FILL,  SE_EDGE,  "square", "Side-effect  (browser · TTS · FFmpeg)"),
    (END_FILL, END_FILL, "pill",   "Start / End"),
]
for i, (fc, ec, shape, txt) in enumerate(legend):
    yy = ly1 - 0.85 - i * 0.52
    sx = lx0 + 0.55
    if shape == "diamond":
        d = 0.16
        ax.add_patch(Polygon([(sx, yy+d), (sx+d, yy), (sx, yy-d), (sx-d, yy)],
                     closed=True, facecolor=fc, edgecolor=ec, lw=1.3, zorder=6))
    elif shape == "pill":
        ax.add_patch(FancyBboxPatch((sx-0.22, yy-0.11), 0.44, 0.22,
                     boxstyle="round,pad=0.02,rounding_size=0.11",
                     facecolor=fc, edgecolor="none", zorder=6))
    else:
        ax.add_patch(FancyBboxPatch((sx-0.2, yy-0.14), 0.4, 0.28,
                     boxstyle="round,pad=0.02,rounding_size=0.06",
                     facecolor=fc, edgecolor=ec, lw=1.3, zorder=6))
    ax.text(sx + 0.55, yy, txt, va="center", fontsize=10.5,
            color=INK, zorder=6)


# ─────────────────────────────────────────────────────────────────────────────
# "At a glance" (right, middle)
# ─────────────────────────────────────────────────────────────────────────────
gx0, gy1 = 13.6, 14.4
panel(gx0, 8.4, 19.6, gy1)
ax.text(gx0 + 0.35, gy1 - 0.4, "At a glance", fontsize=13,
        color=INK, fontweight="bold", zorder=6)

glance = [
    "Two videos per run: narrated + silent",
    "Gemini used once per run (script only)",
    "Edge TTS voice-over — free, no quota",
    "Human approves the script before render",
    "Works for platform or local agents",
    "All platform selectors live in one file",
    "FFmpeg assembles + validates both cuts",
    "Intermediates auto-cleaned on finalize",
]
for i, txt in enumerate(glance):
    yy = gy1 - 1.0 - i * 0.62
    ax.text(gx0 + 0.55, yy, "•", fontsize=14, color=TITLE_B,
            va="center", fontweight="bold", zorder=6)
    ax.text(gx0 + 0.9, yy, txt, fontsize=10.8, color=INK,
            va="center", zorder=6)


# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "docs", "architecture.png")
plt.savefig(out_path, dpi=DPI, bbox_inches="tight",
            facecolor=PAGE, edgecolor="none", pad_inches=0.15)
plt.close()
print("Saved -> docs/architecture.png")
