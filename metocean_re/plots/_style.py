"""Colours and helpers shared by all figures."""

import matplotlib.pyplot as plt

from ..stats import turbines
from ..stats.stability import CLASS_NAMES

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Colour-blind checked categorical palette, always used in this order.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
MAGENTA = "#e87ba4"
GREEN = "#008300"
VIOLET = "#4a3aa7"
RED = "#e34948"
CATEGORICAL = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

# Stability classes: diverging red (unstable) - grey (neutral) - blue (stable)
STABILITY_COLORS = dict(zip(CLASS_NAMES, [
    "#a8201f", "#e34948", "#f19a99",  # very unstable, unstable, near-neutral unstable
    "#b5b4ad",                        # neutral
    "#86b6ef", "#2a78d6", "#104281",  # near-neutral stable, stable, very stable
]))

# Text, grid and background colours
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID_COLOR = "#e1e0d9"
BASELINE = "#c3c2b7"
SHADE = "#f0efec"
SURFACE = "#fcfcfb"

DASHED = (0, (4, 3))

# Space at the top of each figure for the title and subtitle [inches]
TITLE_SPACE = 0.55


def turbine_color(turbine):
    """Each turbine keeps the same colour in every figure."""
    index = turbines.names().index(turbine.name) if turbine.name in turbines.names() else 0
    return CATEGORICAL[index % len(CATEGORICAL)]


def style_axes(ax, grid_axis="y"):
    """Light grid, no top/right frame."""
    ax.set_facecolor(SURFACE)
    ax.grid(axis=grid_axis, color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(BASELINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)


def titles(fig, title, subtitle):
    """Figure title (what is shown) and subtitle (the main result)."""
    height = fig.get_figheight()
    fig.suptitle(title, x=0.01, y=1 - 0.1 / height, ha="left", va="top", fontsize=13, color=INK)
    fig.text(0.01, 1 - 0.42 / height, subtitle, ha="left", va="top", fontsize=9.5, color=INK_SECONDARY)


def finish(fig, output_file):
    """Lay out the figure, then save and close it if output_file is given."""
    fig.set_facecolor(SURFACE)
    fig.tight_layout(rect=(0, 0, 1, 1 - TITLE_SPACE / fig.get_figheight()))
    if output_file:
        fig.savefig(output_file, dpi=150, facecolor=SURFACE)
        plt.close(fig)
    return fig


def label_line(ax, y, text, color=INK_MUTED, x=0.99):
    """Horizontal reference line with a label at the right end."""
    ax.axhline(y, color=color, linewidth=1, linestyle=DASHED, zorder=2)
    ax.text(x, y, text, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8.5,
            color=INK_SECONDARY, zorder=5, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5))


def line_with_markers(ax, x, y, color, label=None, **kwargs):
    """2 px line with 7 px markers ringed in the background colour."""
    return ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=7, markeredgecolor=SURFACE,
                   markeredgewidth=1.5, zorder=3, label=label, **kwargs)


def stability_axis(ax, rotation=30):
    """x-axis ticks for the stability classes."""
    ax.set_xticks(range(len(CLASS_NAMES)), CLASS_NAMES, rotation=rotation, ha="right")
