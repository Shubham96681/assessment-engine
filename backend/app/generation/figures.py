"""
Figure Generation Engine — All figure types via matplotlib
"""
import os
import uuid
import string
import logging
import asyncio
from typing import Dict, Any, Optional

# Any single-letter label A–Z is supported for geometry diagrams
GEOMETRY_POINT_LABELS = frozenset(string.ascii_uppercase)

import matplotlib
matplotlib.use("Agg")  # must be before pyplot — avoids tkinter hang in background tasks

from app.core.config import settings

logger = logging.getLogger(__name__)
FIGURES_DIR = os.path.abspath(os.path.join(settings.LOCAL_STORAGE_PATH, "figures"))


def _geometry_fonts() -> Dict[str, float]:
    """Central font sizes for NCERT-style labeled diagrams."""
    return {
        "point_label": float(settings.FIGURE_POINT_LABEL_FONT_PT),
        "segment_label": float(settings.FIGURE_SEGMENT_LABEL_FONT_PT),
        "title": float(settings.FIGURE_TITLE_FONT_PT),
        "marker": float(settings.FIGURE_POINT_MARKER_SIZE),
    }


def _print_geometry_figure():
    """High-DPI white canvas for PDF embedding (avoids blurry downscale)."""
    import matplotlib.pyplot as plt

    dpi = max(120, int(settings.FIGURE_EXPORT_DPI))
    return plt.subplots(figsize=(10.5, 8.5), dpi=dpi)


def _setup_dark_fig(w=8, h=5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")
    return fig, ax


class FigureGenerator:
    COLORS = ["#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6", "#06b6d4"]

    async def generate(self, spec: Dict[str, Any], figure_type: str) -> Optional[str]:
        os.makedirs(FIGURES_DIR, exist_ok=True)
        fig_id = str(uuid.uuid4())[:8]
        try:
            dispatch = {
                "flowchart": self._flowchart,
                "process_diagram": self._flowchart,
                "bar_graph": self._bar_graph,
                "line_graph": self._line_graph,
                "mind_map": self._mind_map,
                "venn_diagram": self._venn,
                "table": self._table,
                "labeled_diagram": self._labeled_diagram,
                "unit_circle": self._unit_circle,
            }
            fn = dispatch.get(figure_type, self._flowchart)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, fn, spec, fig_id)
        except Exception as e:
            logger.error(f"Figure error ({figure_type}): {e}")
            return None

    def _save(
        self,
        fig,
        name: str,
        fig_id: str,
        facecolor: str = "#0f172a",
        dpi: int | None = None,
    ) -> str:
        import matplotlib.pyplot as plt

        dpi = dpi or settings.FIGURE_EXPORT_DPI
        path = os.path.join(FIGURES_DIR, f"{name}_{fig_id}.png")
        fig.savefig(
            path,
            dpi=dpi,
            bbox_inches="tight",
            facecolor=facecolor,
            pad_inches=0.12,
        )
        plt.close(fig)
        return f"/uploads/figures/{name}_{fig_id}.png"

    def _unit_circle(self, spec: Dict, fig_id: str) -> str:
        """NCERT-style unit circle with θ in standard position."""
        import math

        import matplotlib.patches as mpatches

        angle_deg = float(spec.get("angle_deg", 45)) % 360
        theta_label = str(spec.get("theta_label") or "θ")
        title = spec.get("title", "Diagram")
        fonts = _geometry_fonts()

        fig, ax = _print_geometry_figure()
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.set_aspect("equal")
        ax.axis("off")

        r = 1.0
        pad = 0.42
        ax.set_xlim(-r - pad, r + pad)
        ax.set_ylim(-r - pad, r + pad)

        if spec.get("show_axes", True):
            ax.axhline(0, color="#94a3b8", lw=0.9, zorder=1)
            ax.axvline(0, color="#94a3b8", lw=0.9, zorder=1)
            ax.annotate(
                "",
                xy=(r + 0.28, 0),
                xytext=(r + 0.05, 0),
                arrowprops=dict(arrowstyle="-|>", color="#64748b", lw=1.0),
            )
            ax.annotate(
                "",
                xy=(0, r + 0.28),
                xytext=(0, r + 0.05),
                arrowprops=dict(arrowstyle="-|>", color="#64748b", lw=1.0),
            )

        ax.add_patch(
            mpatches.Circle(
                (0, 0),
                r,
                fill=False,
                edgecolor="#1e293b",
                lw=2.2,
                zorder=2,
            )
        )

        rad = math.radians(angle_deg)
        x_end, y_end = math.cos(rad), math.sin(rad)
        ax.plot([0, x_end], [0, y_end], color="#4f46e5", lw=2.0, zorder=4)
        ax.plot(x_end, y_end, "o", color="#4f46e5", markersize=fonts["marker"], zorder=5)

        arc_r = 0.38
        theta2 = angle_deg if angle_deg >= 0 else angle_deg + 360
        ax.add_patch(
            mpatches.Arc(
                (0, 0),
                2 * arc_r,
                2 * arc_r,
                angle=0,
                theta1=0,
                theta2=theta2,
                color="#4f46e5",
                lw=1.6,
                zorder=3,
            )
        )
        mid = math.radians(theta2 / 2.0)
        ax.text(
            arc_r * 1.15 * math.cos(mid),
            arc_r * 1.15 * math.sin(mid),
            theta_label,
            ha="center",
            va="center",
            fontsize=fonts["segment_label"],
            color="#4f46e5",
            fontweight="bold",
        )
        ax.text(
            x_end + 0.08,
            y_end + 0.08,
            f"{int(angle_deg) if angle_deg == int(angle_deg) else angle_deg}°",
            fontsize=fonts["segment_label"],
            color="#1e293b",
        )

        if spec.get("show_quadrant_labels"):
            qpos = [(0.55, 0.55), (-0.55, 0.55), (-0.55, -0.55), (0.55, -0.55)]
            for i, (qx, qy) in enumerate(qpos, start=1):
                ax.text(
                    qx,
                    qy,
                    f"Q{i}",
                    ha="center",
                    va="center",
                    fontsize=fonts["segment_label"],
                    color="#64748b",
                )

        ax.set_title(
            title,
            color="#000000",
            fontsize=fonts["title"],
            fontweight="bold",
            pad=10,
            loc="left",
        )
        return self._save(fig, "diagram", fig_id, facecolor="#ffffff")

    def _flowchart(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        nodes = spec.get("nodes", ["Start", "Process", "End"])
        edges = spec.get("edges", [])
        title = spec.get("title", "Flowchart")
        labels = spec.get("labels", {})

        fig, ax = plt.subplots(figsize=(8, max(4, len(nodes) * 1.8)))
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, len(nodes) * 2.2 + 1)
        ax.axis("off")

        node_pos = {}
        for i, node in enumerate(nodes):
            y = len(nodes) * 2 - i * 2
            x = 5
            node_pos[node] = (x, y)
            color = self.COLORS[i % len(self.COLORS)]
            rect = plt.Rectangle((x - 2, y - 0.45), 4, 0.9,
                                  color=color, alpha=0.9, zorder=4)
            ax.add_patch(rect)
            ax.text(x, y, node, ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold", zorder=5)
            lbl = labels.get(node, "")
            if lbl:
                ax.text(x + 2.3, y, lbl, ha="left", va="center",
                        color="#a5b4fc", fontsize=7, style="italic")

        for edge in edges:
            if len(edge) == 2 and edge[0] in node_pos and edge[1] in node_pos:
                x1, y1 = node_pos[edge[0]]
                x2, y2 = node_pos[edge[1]]
                ax.annotate("", xy=(x2, y2 + 0.45), xytext=(x1, y1 - 0.45),
                            arrowprops=dict(arrowstyle="->", color="#818cf8", lw=2))

        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        return self._save(fig, "flowchart", fig_id)

    def _bar_graph(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        labels = spec.get("labels", ["A", "B", "C", "D"])
        values = spec.get("values", [4, 7, 3, 8])
        title = spec.get("title", "Bar Graph")

        fig, ax = _setup_dark_fig()
        bars = ax.bar(labels, values, color=self.COLORS[:len(labels)],
                      edgecolor="white", linewidth=0.5)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(v), ha="center", va="bottom", color="white", fontsize=9)
        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        ax.tick_params(colors="white")
        ax.set_xlabel(spec.get("x_label", ""), color="#94a3b8")
        ax.set_ylabel(spec.get("y_label", ""), color="#94a3b8")
        for sp in ax.spines.values():
            sp.set_edgecolor("#334155")
        ax.grid(axis="y", color="#334155", linestyle="--", alpha=0.4)
        return self._save(fig, "bar", fig_id)

    def _line_graph(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        x = spec.get("x", [1, 2, 3, 4, 5])
        y = spec.get("y", [2, 4, 3, 7, 6])
        title = spec.get("title", "Line Graph")

        fig, ax = _setup_dark_fig()
        ax.plot(x, y, color="#6366f1", lw=2.5, marker="o",
                markersize=7, markerfacecolor="#ec4899", markeredgecolor="white")
        ax.fill_between(x, y, alpha=0.12, color="#6366f1")
        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        ax.tick_params(colors="white")
        ax.set_xlabel(spec.get("x_label", ""), color="#94a3b8")
        ax.set_ylabel(spec.get("y_label", ""), color="#94a3b8")
        for sp in ax.spines.values():
            sp.set_edgecolor("#334155")
        ax.grid(color="#334155", linestyle="--", alpha=0.4)
        return self._save(fig, "line", fig_id)

    def _mind_map(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        import numpy as np
        center = spec.get("center", "Main Topic")
        branches = spec.get("branches", ["Branch 1", "Branch 2", "Branch 3"])
        title = spec.get("title", "Mind Map")

        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")
        ax.set_xlim(-6, 6); ax.set_ylim(-5, 5); ax.axis("off")
        ax.add_patch(plt.Circle((0, 0), 0.9, color="#6366f1", zorder=5))
        ax.text(0, 0, center, ha="center", va="center",
                color="white", fontsize=9, fontweight="bold", zorder=6)
        n = len(branches)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        for i, (branch, angle) in enumerate(zip(branches, angles)):
            bx = 3.5 * np.cos(angle); by = 3.5 * np.sin(angle)
            ax.plot([0, bx], [0, by], color=self.COLORS[i % len(self.COLORS)],
                    lw=2, alpha=0.7, zorder=3)
            ax.add_patch(plt.Circle((bx, by), 0.75,
                                     color=self.COLORS[i % len(self.COLORS)],
                                     alpha=0.85, zorder=4))
            ax.text(bx, by, branch, ha="center", va="center",
                    color="white", fontsize=8, fontweight="bold", zorder=5)
        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        return self._save(fig, "mindmap", fig_id)

    def _venn(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        sets = spec.get("sets", ["Set A", "Set B"])
        labels = spec.get("labels", {"left": "Only A", "right": "Only B", "center": "A ∩ B"})
        title = spec.get("title", "Venn Diagram")

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor("#0f172a"); ax.set_facecolor("#0f172a")
        ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
        ax.add_patch(mpatches.Circle((3.5, 4), 2.2, color="#6366f1", alpha=0.5))
        ax.add_patch(mpatches.Circle((6.5, 4), 2.2, color="#ec4899", alpha=0.5))
        ax.add_patch(mpatches.Circle((3.5, 4), 2.2, fill=False, edgecolor="#818cf8", lw=2))
        ax.add_patch(mpatches.Circle((6.5, 4), 2.2, fill=False, edgecolor="#f9a8d4", lw=2))
        ax.text(3.5, 4, sets[0], ha="center", va="center", color="white",
                fontsize=11, fontweight="bold")
        ax.text(6.5, 4, sets[1] if len(sets) > 1 else "Set B",
                ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        ax.text(2.0, 4, labels.get("left", ""), ha="center", va="center",
                color="#c7d2fe", fontsize=8)
        ax.text(8.0, 4, labels.get("right", ""), ha="center", va="center",
                color="#fbcfe8", fontsize=8)
        ax.text(5.0, 4, labels.get("center", ""), ha="center", va="center",
                color="white", fontsize=8, fontweight="bold")
        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        return self._save(fig, "venn", fig_id)

    def _table(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        headers = spec.get("headers", ["Col 1", "Col 2", "Col 3"])
        rows = spec.get("rows", [["A", "B", "C"]])
        title = spec.get("title", "Table")

        fig, ax = plt.subplots(figsize=(10, max(3, len(rows) * 0.7 + 1.5)))
        fig.patch.set_facecolor("#0f172a"); ax.set_facecolor("#0f172a"); ax.axis("off")
        tbl = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
        tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1, 1.8)
        for j in range(len(headers)):
            tbl[(0, j)].set_facecolor("#4f46e5")
            tbl[(0, j)].set_text_props(color="white", fontweight="bold")
        for i in range(1, len(rows) + 1):
            for j in range(len(headers)):
                tbl[(i, j)].set_facecolor("#1e293b" if i % 2 == 0 else "#0f172a")
                tbl[(i, j)].set_text_props(color="white")
                tbl[(i, j)].set_edgecolor("#334155")
        ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=20)
        return self._save(fig, "table", fig_id)

    @staticmethod
    def _looks_like_circle_geometry(spec: Dict) -> bool:
        elements = spec.get("elements") or []
        if any((el.get("shape") or "").lower() == "circle" for el in elements):
            return True
        point_positions = {
            (el.get("position") or "").lower()
            for el in elements
            if (el.get("shape") or "").lower() == "point"
        }
        if point_positions & {"on_circle", "outside", "centre", "center"}:
            return True
        labels = {(el.get("label") or "").upper() for el in elements}
        if "O" in labels and len(
            [el for el in elements if (el.get("shape") or "").lower() == "segment"]
        ) >= 2:
            return True
        return False

    def _labeled_diagram(self, spec: Dict, fig_id: str) -> str:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        elements = spec.get("elements")
        if elements:
            if self._looks_like_circle_geometry(spec):
                if not any(
                    (el.get("shape") or "").lower() == "circle" for el in elements
                ):
                    spec = dict(spec)
                    spec["elements"] = [
                        {"shape": "circle", "label": "Circle"},
                        *list(spec["elements"]),
                    ]
                return self._geometry_diagram(spec, fig_id)
            return self._rectangle_diagram(spec, fig_id)

        components = spec.get("components", [
            {"name": "A", "x": 0.3, "y": 0.7, "label": "Part A"},
            {"name": "B", "x": 0.7, "y": 0.3, "label": "Part B"},
        ])
        title = spec.get("title", "Labeled Diagram")
        connections = spec.get("connections", [])

        fig, ax = plt.subplots(figsize=(9, 7))
        fig.patch.set_facecolor("#0f172a"); ax.set_facecolor("#0f172a")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        pos_map = {}
        for i, c in enumerate(components):
            x, y = c.get("x", 0.5), c.get("y", 0.5)
            name = c.get("name", f"C{i+1}")
            pos_map[name] = (x, y)
            color = self.COLORS[i % len(self.COLORS)]
            ax.add_patch(plt.Circle((x, y), 0.05, color=color, zorder=5, alpha=0.9))
            ax.text(x, y, str(i + 1), ha="center", va="center",
                    color="white", fontsize=8, fontweight="bold", zorder=6)
            ax.text(x + 0.07, y, f"{name}: {c.get('label', '')}",
                    ha="left", va="center", color="#e2e8f0", fontsize=8)
        for conn in connections:
            if len(conn) == 2 and conn[0] in pos_map and conn[1] in pos_map:
                x1, y1 = pos_map[conn[0]]; x2, y2 = pos_map[conn[1]]
                ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                            arrowprops=dict(arrowstyle="->", color="#818cf8", lw=1.5))
        ax.set_title(title, color="white", fontsize=12, fontweight="bold")
        return self._save(fig, "diagram", fig_id)

    def _rectangle_diagram(self, spec: Dict, fig_id: str) -> str:
        """Area / word-problem layouts — rectangle + segments, no default circle."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        title = spec.get("title", "Diagram")
        elements = spec.get("elements", [])
        labels = spec.get("labels", {})
        fig, ax = plt.subplots(figsize=(9, 6))
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.set_aspect("equal")
        ax.axis("off")

        points: Dict[str, tuple] = {}
        point_els = [el for el in elements if (el.get("shape") or "").lower() == "point"]
        n = max(len(point_els), 4)
        for i, el in enumerate(point_els):
            lbl = el.get("label", f"P{i}")
            if n <= 4:
                coords = [(1, 1), (5, 1), (5, 3), (1, 3)]
                points[lbl] = coords[i % 4]
            else:
                points[lbl] = (1 + (i % 4) * 1.2, 1 + (i // 4) * 1.0)

        if len(points) >= 4:
            ordered = list(points.values())[:4]
            rect = mpatches.Polygon(
                ordered + [ordered[0]],
                fill=False,
                edgecolor="#1e293b",
                lw=2,
            )
            ax.add_patch(rect)

        for el in elements:
            if (el.get("shape") or "").lower() != "segment":
                continue
            a, b = el.get("from"), el.get("to")
            if a in points and b in points:
                x1, y1 = points[a]
                x2, y2 = points[b]
                ax.plot([x1, x2], [y1, y2], color="#1e293b", lw=1.8)
                mid = el.get("label")
                if mid:
                    ax.text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        mid,
                        fontsize=9,
                        ha="center",
                        color="#334155",
                    )

        for lbl, (x, y) in points.items():
            ax.plot(x, y, "o", color="#4f46e5", ms=6)
            ax.text(
                x,
                y - 0.15,
                labels.get(lbl, lbl),
                fontsize=10,
                ha="center",
                fontweight="bold",
            )

        ax.set_xlim(-3.2, 3.2)
        ax.set_ylim(-2.8, 3.2)
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        return self._save(fig, "diagram", fig_id, facecolor="#ffffff")

    def _two_circle_external_tangent_diagram(self, spec: Dict, fig_id: str) -> str:
        """Two separate circles with a direct common external tangent (slot Q4)."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        fonts = _geometry_fonts()
        centres = spec.get("centres") or ["G", "H"]
        c1, c2 = centres[0], centres[1] if len(centres) > 1 else "H"
        radii_map = spec.get("radii") or {}
        r1 = float(radii_map.get(c1, 3))
        r2 = float(radii_map.get(c2, 8))
        d = float(spec.get("centre_distance") or 13)
        tan_seg = spec.get("tangent_segment") or ["E", "F"]
        e, f = tan_seg[0], tan_seg[1] if len(tan_seg) > 1 else "F"
        labels = spec.get("labels") or {}

        # Draw proportional radii with centres separated (no nested overlap)
        r_max = max(r1, r2, 1.0)
        unit = 2.0 / r_max
        r1s, r2s = r1 * unit, r2 * unit
        gap = 0.45
        x1 = 0.0
        x2 = r1s + gap + r2s
        # Stretch horizontally if real centre distance is larger than touching layout
        min_span = (d / r_max) * 1.15
        if x2 < min_span:
            x2 = min_span
            x1 = 0.0

        fig, ax = _print_geometry_figure()
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.set_aspect("equal")
        ax.axis("off")

        ax.add_patch(
            mpatches.Circle((x1, r1s), r1s, fill=False, edgecolor="#1e293b", lw=2.4)
        )
        ax.add_patch(
            mpatches.Circle((x2, r2s), r2s, fill=False, edgecolor="#1e293b", lw=2.4)
        )

        # External tangent above both circles (same side)
        y_top1 = 2 * r1s + 0.25
        y_top2 = 2 * r2s + 0.25
        y_off = max(y_top1, y_top2)
        ax.plot(
            [x1, x2],
            [y_off, y_off],
            color="#000000",
            lw=1.6,
        )
        ax.plot(
            [x1, x2],
            [r1s, r2s],
            color="#64748b",
            lw=1.0,
            linestyle="--",
        )

        points = {
            c1: (x1, r1s),
            c2: (x2, r2s),
            e: (x1, y_off),
            f: (x2, y_off),
        }
        for name, (px, py) in points.items():
            ax.plot(px, py, "o", color="#000000", markersize=fonts["marker"], zorder=5)
            ax.text(
                px + 0.22,
                py + 0.22,
                labels.get(name, name),
                fontsize=fonts["point_label"],
                fontweight="bold",
                color="#000000",
            )

        ax.set_xlim(x1 - r1s - 0.8, x2 + r2s + 0.8)
        ax.set_ylim(-0.5, y_off + 0.9)
        return self._save(fig, "diagram", fig_id, facecolor="#ffffff")

    def _geometry_diagram(self, spec: Dict, fig_id: str) -> str:
        """Render NCERT-style geometry from figure_spec.elements (circle, point, line, segment)."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        if spec.get("layout") == "two_circle_external_tangent":
            return self._two_circle_external_tangent_diagram(spec, fig_id)

        title = spec.get("title", "Figure")
        elements = spec.get("elements", [])
        labels = spec.get("labels", {})

        fonts = _geometry_fonts()
        fig, ax = _print_geometry_figure()
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.set_aspect("equal")
        ax.axis("off")

        circle_patch = None
        centre = (0.0, 0.0)
        radius = 2.0
        inner_radius_ratio: Optional[float] = None
        points: Dict[str, tuple] = {}

        for el in elements:
            shape = (el.get("shape") or "").lower()
            if shape == "circle":
                ratio = el.get("radius_ratio")
                if ratio is not None:
                    try:
                        inner_radius_ratio = float(ratio)
                    except (TypeError, ValueError):
                        pass
                    continue
                centre = (0.0, 0.0)
                radius = 2.0
                circle_patch = mpatches.Circle(
                    centre, radius, fill=False, edgecolor="#1e293b", lw=2.4
                )
                ax.add_patch(circle_patch)

        if circle_patch is None:
            circle_patch = mpatches.Circle((0, 0), 2, fill=False, edgecolor="#1e293b", lw=2.4)
            ax.add_patch(circle_patch)

        if inner_radius_ratio is not None and 0 < inner_radius_ratio < 1:
            r_in = radius * inner_radius_ratio
            ax.add_patch(
                mpatches.Circle(
                    centre,
                    r_in,
                    fill=False,
                    edgecolor="#475569",
                    lw=2.0,
                    linestyle="--",
                )
            )

        def _label_slot(label: str) -> int:
            """Stable 0–25 slot for A–Z (multi-char labels hash into range)."""
            label = (label or "").strip().upper()
            if len(label) == 1 and label in GEOMETRY_POINT_LABELS:
                return ord(label) - ord("A")
            return sum(ord(c) for c in label) % 26

        point_els = [el for el in elements if (el.get("shape") or "").lower() == "point"]
        on_circle_labels = [
            el.get("label")
            for el in point_els
            if (el.get("position") or "").lower() == "on_circle" and el.get("label")
        ]
        inside_labels = [
            el.get("label")
            for el in point_els
            if (el.get("position") or "").lower() == "inside" and el.get("label")
        ]
        outside_labels = [
            el.get("label")
            for el in point_els
            if (el.get("position") or "").lower() == "outside" and el.get("label")
        ]

        def _tangent_contacts_from_external(ext_label: str) -> list[str]:
            contacts: list[str] = []
            for el in elements:
                if (el.get("shape") or "").lower() != "segment":
                    continue
                frm, to = el.get("from"), el.get("to")
                if frm == ext_label and to in on_circle_labels:
                    contacts.append(to)
                elif to == ext_label and frm in on_circle_labels:
                    contacts.append(frm)
            return contacts

        def _apply_external_tangent_pair_layout(ext_label: str, c1: str, c2: str) -> None:
            """Two tangents from P — contacts must not be diameter-opposite (invalid finite P)."""
            d = radius + 1.15
            points[ext_label] = (-d, 0.0)
            alpha = float(np.arcsin(min(0.95, radius / d)))
            ang_a = np.pi / 2 + alpha * 0.92
            ang_b = -np.pi / 2 - alpha * 0.92
            points[c1] = (radius * np.cos(ang_a), radius * np.sin(ang_a))
            points[c2] = (radius * np.cos(ang_b), radius * np.sin(ang_b))

        def _apply_external_secant_tangent_layout(
            ext_label: str, tangent_contact: str, secant_contacts: list[str]
        ) -> None:
            """One tangent + secant through two circle points from the same external point."""
            d = radius + 1.2
            points[ext_label] = (-d, 0.0)
            alpha = float(np.arcsin(min(0.95, radius / d)))
            points[tangent_contact] = (
                radius * np.cos(np.pi / 2 + alpha * 0.85),
                radius * np.sin(np.pi / 2 + alpha * 0.85),
            )
            b, c = secant_contacts[0], secant_contacts[1]
            ang_b = -0.55
            ang_c = 0.42
            points[b] = (radius * np.cos(ang_b), radius * np.sin(ang_b))
            points[c] = (radius * np.cos(ang_c), radius * np.sin(ang_c))

        def _apply_fusion_q5_layout(
            p_ext: str,
            p_contact: str,
            g_ext: str,
            g_contact: str,
            secant_a: str,
            secant_b: str,
            centre_lbl: str,
        ) -> None:
            """Q5: concentric circles + P/A (Q2) on the left + G/H/J/K below — distinct from Q2."""
            d = radius + 1.25
            points[centre_lbl] = (0.0, 0.0)
            points[p_ext] = (-d, 0.12)
            alpha_p = float(np.arcsin(min(0.95, radius / d)))
            points[p_contact] = (
                radius * np.cos(np.pi / 2 + alpha_p * 0.82),
                radius * np.sin(np.pi / 2 + alpha_p * 0.82),
            )
            points[g_ext] = (-d * 0.5, -d * 0.92)
            points[g_contact] = (
                radius * np.cos(-0.42),
                radius * np.sin(-0.42),
            )
            points[secant_a] = (radius * np.cos(-0.82), radius * np.sin(-0.82))
            points[secant_b] = (radius * np.cos(0.08), radius * np.sin(0.08))

        def _apply_concentric_chord_layout(
            centre_lbl: str,
            chord_a: str,
            chord_b: str,
            contact_lbl: str,
        ) -> None:
            """Chord of outer circle tangent to inner circle at contact (not through centre)."""
            points[centre_lbl] = (0.0, 0.0)
            r_in = radius * (inner_radius_ratio or 0.55)
            y_chord = -r_in
            points[contact_lbl] = (0.0, y_chord)
            half = float(np.sqrt(max(radius * radius - y_chord * y_chord, 0.25)))
            points[chord_a] = (-half, y_chord)
            points[chord_b] = (half, y_chord)

        def _apply_tangent_at_contact_layout(
            centre_lbl: str, contact_lbl: str, ext_lbl: str
        ) -> None:
            """Tangent at contact on circle; external point off the tangent line."""
            points[centre_lbl] = (0.0, 0.0)
            points[contact_lbl] = (radius * 0.98, 0.0)
            points[ext_lbl] = (radius + 1.35, 1.55)

        concentric_applied = False
        tangent_at_contact_applied = False
        if inner_radius_ratio is not None:
            centre_lbl = next(
                (
                    el.get("label")
                    for el in point_els
                    if (el.get("position") or "").lower() in ("centre", "center")
                ),
                "O",
            )
            chord_segs = [
                el
                for el in elements
                if (el.get("shape") or "").lower() == "segment"
                and el.get("from") in on_circle_labels
                and el.get("to") in on_circle_labels
                and el.get("from") != el.get("to")
            ]
            contact_candidates = [
                el.get("label")
                for el in point_els
                if (el.get("position") or "").lower() == "on_circle"
                and el.get("label")
                and el.get("label") != centre_lbl
            ]
            dashed_to_contact = [
                el.get("to")
                for el in elements
                if (el.get("shape") or "").lower() == "segment"
                and el.get("from") == centre_lbl
                and el.get("style") == "dashed"
                and el.get("to") in contact_candidates
            ]
            if chord_segs and dashed_to_contact:
                cs = chord_segs[0]
                contact = dashed_to_contact[0]
                _apply_concentric_chord_layout(centre_lbl, cs.get("from"), cs.get("to"), contact)
                concentric_applied = True

        if not concentric_applied and len(outside_labels) == 1 and len(on_circle_labels) >= 1:
            centre_lbl = next(
                (
                    el.get("label")
                    for el in point_els
                    if (el.get("position") or "").lower() in ("centre", "center")
                ),
                "O",
            )
            ext = outside_labels[0]
            for el in elements:
                if (el.get("shape") or "").lower() != "segment":
                    continue
                frm, to = el.get("from"), el.get("to")
                if frm == ext and to in on_circle_labels and to != centre_lbl:
                    has_radius = any(
                        (e.get("from") == centre_lbl and e.get("to") == to and e.get("style") == "dashed")
                        for e in elements
                        if (e.get("shape") or "").lower() == "segment"
                    )
                    if has_radius:
                        other_tangents = [
                            e.get("to")
                            for e in elements
                            if (e.get("shape") or "").lower() == "segment"
                            and e.get("from") == ext
                            and e.get("to") in on_circle_labels
                        ]
                        if len(other_tangents) < 2:
                            _apply_tangent_at_contact_layout(centre_lbl, to, ext)
                            tangent_at_contact_applied = True
                            break

        fusion_q5_applied = False
        if spec.get("layout") == "fusion_q5" and len(outside_labels) >= 2:
            centre_lbl = next(
                (
                    el.get("label")
                    for el in point_els
                    if (el.get("position") or "").lower() in ("centre", "center")
                ),
                "O",
            )
            q2_ext, fusion_ext = outside_labels[0], outside_labels[1]
            q2_contacts = _tangent_contacts_from_external(q2_ext)
            fusion_contacts = _tangent_contacts_from_external(fusion_ext)
            sec_pts = [
                lbl
                for lbl in on_circle_labels
                if lbl not in q2_contacts + fusion_contacts
            ][:2]
            if q2_contacts and fusion_contacts and len(sec_pts) >= 2:
                _apply_fusion_q5_layout(
                    q2_ext,
                    q2_contacts[0],
                    fusion_ext,
                    fusion_contacts[0],
                    sec_pts[0],
                    sec_pts[1],
                    centre_lbl,
                )
                fusion_q5_applied = True

        tangent_pair_applied = False
        secant_tangent_applied = False
        if (
            not concentric_applied
            and not tangent_at_contact_applied
            and not fusion_q5_applied
            and len(outside_labels) == 1
            and len(on_circle_labels) >= 2
        ):
            ext = outside_labels[0]
            contacts = _tangent_contacts_from_external(ext)
            if len(contacts) >= 2:
                _apply_external_tangent_pair_layout(ext, contacts[0], contacts[1])
                tangent_pair_applied = True
            elif len(contacts) == 1 and len(on_circle_labels) >= 3:
                tangent_pt = contacts[0]
                secant_pts = [lbl for lbl in on_circle_labels if lbl != tangent_pt][:2]
                if len(secant_pts) == 2:
                    _apply_external_secant_tangent_layout(ext, tangent_pt, secant_pts)
                    secant_tangent_applied = True

        for el in point_els:
            label = el.get("label", "")
            if not label:
                continue
            if (
                concentric_applied
                or tangent_at_contact_applied
                or tangent_pair_applied
                or secant_tangent_applied
                or fusion_q5_applied
            ) and label in points:
                continue
            pos_hint = (el.get("position") or "").lower()
            if pos_hint in ("centre", "center"):
                points[label] = (0.0, 0.0)
            elif pos_hint == "on_circle":
                idx = on_circle_labels.index(label) if label in on_circle_labels else 0
                n = max(len(on_circle_labels), 1)
                slot = _label_slot(label)
                # Avoid placing exactly 2 points at 0° and 180° (false diameter through O)
                if n == 2:
                    spread = 0.95 + slot * 0.02
                    ang = (np.pi / 2 + spread / 2) if idx == 0 else (-np.pi / 2 - spread / 2)
                else:
                    ang = (2 * np.pi * idx / n) + (np.pi / 6) + (slot * 0.04)
                points[label] = (radius * np.cos(ang), radius * np.sin(ang))
            elif pos_hint == "inside":
                idx = inside_labels.index(label) if label in inside_labels else _label_slot(label)
                angle = (idx * 1.15) + (_label_slot(label) * 0.2)
                r_in = 0.35 + (idx % 3) * 0.12
                points[label] = (r_in * np.cos(angle), r_in * np.sin(angle))
            elif pos_hint == "outside":
                idx = outside_labels.index(label) if label in outside_labels else _label_slot(label)
                slot = _label_slot(label)
                points[label] = (
                    -0.8 + 0.35 * idx + 0.05 * (slot % 5),
                    radius + 0.85 + 0.12 * (slot // 5),
                )
            else:
                slot = _label_slot(label)
                points[label] = (0.2 * (slot % 5), radius + 0.9 + 0.08 * (slot // 5))

        # Interior point on a secant chord: segment joins two on-circle points
        for el in elements:
            if (el.get("shape") or "").lower() != "segment":
                continue
            frm, to = el.get("from"), el.get("to")
            if frm not in points or to not in points:
                continue
            if frm not in on_circle_labels or to not in on_circle_labels:
                continue
            x1, y1 = points[frm]
            x2, y2 = points[to]
            for inl in inside_labels:
                points[inl] = (x1 + 0.42 * (x2 - x1), y1 + 0.42 * (y2 - y1))

        for name, (x, y) in points.items():
            ax.plot(
                x,
                y,
                "o",
                color="#000000",
                markersize=fonts["marker"],
                zorder=5,
            )
            offset = labels.get(name, name)
            dist = (x * x + y * y) ** 0.5
            label_off = 0.30
            if dist > 0.15:
                lx, ly = x + label_off * x / dist, y + label_off * y / dist
            else:
                lx, ly = x + 0.26, y + 0.26
            ax.text(
                lx,
                ly,
                offset,
                fontsize=fonts["point_label"],
                color="#000000",
                fontweight="bold",
                bbox=dict(
                    boxstyle="round,pad=0.22",
                    facecolor="white",
                    edgecolor="#94a3b8",
                    alpha=0.92,
                    linewidth=0.4,
                ),
            )

        for el in elements:
            shape = (el.get("shape") or "").lower()
            label = el.get("label", "")
            style = el.get("style", "")
            if shape in ("line", "ray", "segment"):
                frm, to = el.get("from"), el.get("to")
                if frm in points and to in points:
                    x1, y1 = points[frm]
                    x2, y2 = points[to]
                else:
                    continue
                ls = "--" if style == "dashed" else "-"
                ax.plot([x1, x2], [y1, y2], color="#000000", lw=1.6, linestyle=ls, zorder=3)
                if label:
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    ax.text(
                        mx,
                        my + 0.18,
                        labels.get(label, label),
                        fontsize=fonts["segment_label"],
                        color="#000000",
                        fontweight="bold",
                    )

        def _draw_right_angle(vertex: str, leg1: str, leg2: str) -> None:
            if vertex not in points or leg1 not in points or leg2 not in points:
                return
            vx, vy = points[vertex]
            legs = []
            for leg in (leg1, leg2):
                lx, ly = points[leg]
                d = (lx - vx, ly - vy)
                ln = (d[0] ** 2 + d[1] ** 2) ** 0.5
                if ln < 1e-6:
                    return
                legs.append((d[0] / ln * 0.3, d[1] / ln * 0.3))
            ax.plot(
                [vx, vx + legs[0][0], vx + legs[0][0] + legs[1][0], vx + legs[1][0], vx],
                [vy, vy + legs[0][1], vy + legs[0][1] + legs[1][1], vy + legs[1][1], vy],
                color="#000000",
                lw=1.1,
                zorder=4,
            )

        def _infer_right_angle_legs(vertex: str) -> tuple[str, str] | None:
            centre_lbl = next(
                (
                    el.get("label")
                    for el in point_els
                    if (el.get("position") or "").lower() in ("centre", "center")
                ),
                "O",
            )
            legs: list[str] = []
            for el in elements:
                if (el.get("shape") or "").lower() != "segment":
                    continue
                frm, to = el.get("from"), el.get("to")
                if frm == vertex and to != vertex:
                    legs.append(to)
                elif to == vertex and frm != vertex:
                    legs.append(frm)
            if centre_lbl in legs:
                others = [x for x in legs if x != centre_lbl]
                if others:
                    return centre_lbl, others[0]
            if len(legs) >= 2:
                return legs[0], legs[1]
            return None

        for tm in spec.get("tangent_marks") or []:
            if tm in points:
                tx, ty = points[tm]
                ax.plot(
                    tx,
                    ty,
                    marker="o",
                    markersize=fonts["marker"] * 0.55,
                    markerfacecolor="#ffffff",
                    markeredgecolor="#000000",
                    markeredgewidth=1.2,
                    zorder=5,
                )

        bisect_at = spec.get("chord_bisect_at")
        if bisect_at and bisect_at in points:
            for el in elements:
                if (el.get("shape") or "").lower() != "segment":
                    continue
                frm, to = el.get("from"), el.get("to")
                if bisect_at in (frm, to) and frm in points and to in points:
                    x1, y1 = points[frm]
                    x2, y2 = points[to]
                    bx, by = points[bisect_at]
                    dx, dy = x2 - x1, y2 - y1
                    ln = (dx ** 2 + dy ** 2) ** 0.5 or 1.0
                    nx, ny = -dy / ln * 0.14, dx / ln * 0.14
                    ax.plot(
                        [bx - nx, bx + nx],
                        [by - ny, by + ny],
                        color="#000000",
                        lw=1.4,
                        zorder=4,
                    )
                    break

        if spec.get("show_right_angle"):
            ra_at = spec.get("right_angle_at")
            ra_legs = spec.get("right_angle_legs")
            if not ra_at:
                for el in elements:
                    if (el.get("shape") or "").lower() == "angle_mark":
                        ra_at = el.get("at") or el.get("label")
                        break
            ra_at = ra_at or "A"
            if not ra_legs or len(ra_legs) < 2:
                inferred = _infer_right_angle_legs(ra_at)
                ra_legs = list(inferred) if inferred else ["O", "A"]
            if len(ra_legs) >= 2:
                _draw_right_angle(ra_at, ra_legs[0], ra_legs[1])

        for pair in spec.get("equal_ticks", []):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            frm, to = pair[0], pair[1]
            if frm in points and to in points:
                x1, y1 = points[frm]
                x2, y2 = points[to]
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                ln = (dx ** 2 + dy ** 2) ** 0.5 or 1.0
                nx, ny = -dy / ln * 0.12, dx / ln * 0.12
                ax.plot([mx - nx, mx + nx], [my - ny, my + ny], color="#000000", lw=1.4, zorder=4)

        pad = 1.45
        ax.set_xlim(-radius - pad, radius + pad)
        ax.set_ylim(-radius - pad, radius + pad + 1.8)
        ax.set_title(
            title,
            color="#000000",
            fontsize=fonts["title"],
            fontweight="bold",
            pad=12,
            loc="left",
        )
        return self._save(fig, "diagram", fig_id, facecolor="#ffffff")
