from __future__ import annotations

import sys
from pathlib import Path

from lifting_loops.models import RotationReductionResult, RotationUtilizationResult


def _pyplot():
    import matplotlib

    if "matplotlib.pyplot" not in sys.modules:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_rotation_reduction(result: RotationReductionResult):
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(result.beta, result.k_rot_1, label="T1")
    ax.plot(result.beta, result.k_rot_3, label="T3")
    ax.plot(result.beta, result.k_rot_4, label="T4")
    ax.set_title("Rotation reduction factors")
    ax.set_xlabel("Beta [deg]")
    ax.set_ylabel("k_rot")
    ax.set_xlim(0, 90)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    return fig, ax


def plot_rotation_utilization(result: RotationUtilizationResult):
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(result.beta, result.mu_rot_1, label="T1")
    ax.plot(result.beta, result.mu_rot_3, label="T3")
    ax.plot(result.beta, result.mu_rot_4, label="T4")
    ax.axhline(1.0, color="black", linewidth=1, linestyle="--", label="limit")
    ax.set_title("Rotation utilization")
    ax.set_xlabel("Beta [deg]")
    ax.set_ylabel("Utilization [-]")
    ax.set_xlim(0, 90)
    ax.set_ylim(bottom=0)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    return fig, ax


def save_rotation_utilization_plot(
    result: RotationUtilizationResult,
    path: str | Path,
    dpi: int = 180,
) -> Path:
    """Save a utilization plot.

    Matplotlib is used when available. If it is not installed, a small Pillow
    fallback writes a PNG, or an SVG fallback writes vector output.
    """

    output = Path(path)
    try:
        fig, _ = plot_rotation_utilization(result)
    except ModuleNotFoundError:
        if output.suffix.lower() == ".svg":
            _save_rotation_utilization_svg(result, output)
        else:
            _save_rotation_utilization_png(result, output)
    else:
        fig.savefig(output, dpi=dpi)
    return output


def _finite_max(*series: list[float]) -> float:
    values = [
        value
        for items in series
        for value in items
        if value != float("inf") and value == value
    ]
    return max(values, default=1.0)


def _save_rotation_utilization_png(result: RotationUtilizationResult, path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1200, 750
    margin_left, margin_right = 95, 35
    margin_top, margin_bottom = 55, 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    ymax = max(1.05, _finite_max(result.mu_rot_1, result.mu_rot_3, result.mu_rot_4) * 1.08)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    def point(beta: float, mu: float) -> tuple[float, float]:
        x = margin_left + beta / 90.0 * plot_width
        y = margin_top + (1.0 - min(mu, ymax) / ymax) * plot_height
        return x, y

    draw.rectangle(
        [margin_left, margin_top, margin_left + plot_width, margin_top + plot_height],
        outline="#333333",
    )
    for tick in range(0, 91, 15):
        x = margin_left + tick / 90.0 * plot_width
        draw.line([(x, margin_top), (x, margin_top + plot_height)], fill="#dddddd")
        draw.text((x - 10, margin_top + plot_height + 14), str(tick), fill="#333333", font=font)

    y_ticks = 5
    for i in range(y_ticks + 1):
        value = ymax * i / y_ticks
        y = margin_top + (1.0 - value / ymax) * plot_height
        draw.line([(margin_left, y), (margin_left + plot_width, y)], fill="#eeeeee")
        draw.text((22, y - 6), f"{value:.2f}", fill="#333333", font=font)

    limit_y = point(0, 1.0)[1]
    draw.line([(margin_left, limit_y), (margin_left + plot_width, limit_y)], fill="#111111", width=2)

    def draw_series(values: list[float], color: str) -> None:
        coords = [point(beta, mu) for beta, mu in zip(result.beta, values) if mu == mu]
        if len(coords) > 1:
            draw.line(coords, fill=color, width=3)

    draw_series(result.mu_rot_1, "#1f77b4")
    draw_series(result.mu_rot_3, "#ff7f0e")
    draw_series(result.mu_rot_4, "#2ca02c")

    draw.text((margin_left, 18), "Rotation utilization", fill="#111111", font=font)
    draw.text((margin_left + plot_width / 2 - 35, height - 35), "Beta [deg]", fill="#111111", font=font)
    draw.text((18, 18), "mu [-]", fill="#111111", font=font)
    draw.text((width - 190, 20), "T1", fill="#1f77b4", font=font)
    draw.text((width - 145, 20), "T3", fill="#ff7f0e", font=font)
    draw.text((width - 100, 20), "T4", fill="#2ca02c", font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _save_rotation_utilization_svg(result: RotationUtilizationResult, path: Path) -> None:
    width, height = 900, 560
    left, right = 75, 25
    top, bottom = 45, 60
    plot_width = width - left - right
    plot_height = height - top - bottom
    ymax = max(1.05, _finite_max(result.mu_rot_1, result.mu_rot_3, result.mu_rot_4) * 1.08)

    def point(beta: float, mu: float) -> tuple[float, float]:
        x = left + beta / 90.0 * plot_width
        y = top + (1.0 - min(mu, ymax) / ymax) * plot_height
        return x, y

    def polyline(values: list[float], color: str) -> str:
        points = " ".join(
            f"{x:.2f},{y:.2f}"
            for x, y in (point(beta, mu) for beta, mu in zip(result.beta, values) if mu == mu)
        )
        return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5" />'

    limit_y = point(0, 1.0)[1]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white" />',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="none" stroke="#333" />',
        f'<line x1="{left}" y1="{limit_y:.2f}" x2="{left + plot_width}" y2="{limit_y:.2f}" stroke="#111" stroke-dasharray="6 5" />',
        polyline(result.mu_rot_1, "#1f77b4"),
        polyline(result.mu_rot_3, "#ff7f0e"),
        polyline(result.mu_rot_4, "#2ca02c"),
        f'<text x="{left}" y="26" font-family="Arial" font-size="18">Rotation utilization</text>',
        f'<text x="{left + plot_width / 2 - 35}" y="{height - 18}" font-family="Arial" font-size="13">Beta [deg]</text>',
        f'<text x="{width - 150}" y="25" font-family="Arial" font-size="13" fill="#1f77b4">T1</text>',
        f'<text x="{width - 105}" y="25" font-family="Arial" font-size="13" fill="#ff7f0e">T3</text>',
        f'<text x="{width - 60}" y="25" font-family="Arial" font-size="13" fill="#2ca02c">T4</text>',
        "</svg>",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
