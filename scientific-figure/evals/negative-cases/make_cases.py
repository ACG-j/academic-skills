# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Generate deliberately defective figures that the lint and the review must catch.

This is the skill's own regression test. A linter that reports nothing is
indistinguishable from a linter that works, unless there are known-bad inputs it is
required to flag. Each case below plants one defect and states which check should fire.

Run: uv run make_cases.py -o .
Then: uv run ../../scripts/sf_lint.py --all case-*.py
"""
import argparse
import textwrap
from pathlib import Path

CASES: dict[str, tuple[str, str]] = {
    "case-01-jet-colormap": (
        "jet colormap on continuous data",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        data = rng.random((20, 20))
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        im = ax.imshow(data, cmap="jet")
        ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
        fig.savefig("case-01.png", dpi=300)
        fig.savefig("case-01.pdf")
        """,
    ),
    "case-02-tiny-font": (
        "4 pt text, unreadable in print",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        # Setting font.size alone does NOT shrink text when the style sets
        # axes.labelsize / xtick.labelsize explicitly — every size must be lowered.
        for key in ("font.size", "axes.labelsize", "xtick.labelsize", "ytick.labelsize",
                    "axes.titlesize", "legend.fontsize"):
            plt.rcParams[key] = 4
        rng = np.random.default_rng(0)
        x = np.linspace(0, 10, 24)
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(x, np.sin(x), "o-")
        ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
        fig.savefig("case-02.png", dpi=300)
        fig.savefig("case-02.pdf")
        """,
    ),
    "case-03-legend-over-data": (
        "legend placed on top of the series",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle", STYLE / "nature.mplstyle"])
        rng = np.random.default_rng(0)
        x = np.linspace(0, 10, 40)
        fig, ax = plt.subplots(figsize=(3.504, 2.6))
        # Three nearly-flat series crossing the middle: a centre legend hides them.
        for i, name in enumerate(["alpha", "beta", "gamma"]):
            ax.plot(x, 1.0 + 0.05 * np.sin(x / (i + 1)) + i * 0.02, "o-", label=f"series {name}")
        ax.set_ylim(0.8, 1.3)
        ax.legend(loc="center", fontsize=9)   # lands on the data
        ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
        fig.savefig("case-03.png", dpi=300)
        fig.savefig("case-03.pdf")
        """,
    ),
    "case-04-no-vector": (
        "PNG only, no vector output",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(np.linspace(0, 5, 20), rng.random(20))
        ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
        fig.savefig("case-04.png", dpi=72)
        """,
    ),
    "case-05-truncated-bar": (
        "bar chart with a nonzero baseline",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        values = [3.1, 3.5, 3.2]          # inline data — also a reproducibility defect
        ax.bar(["A", "B", "C"], values)
        ax.set_ylim(3.0, 3.6)             # exaggerates a 0.4 difference
        ax.set_xlabel("Group"); ax.set_ylabel("Score (a.u.)")
        fig.savefig("case-05.png", dpi=300)
        fig.savefig("case-05.pdf")
        """,
    ),
    "case-06-no-units": (
        "axes labelled without units or symbols",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(np.linspace(0, 5, 20), rng.random(20))
        ax.set_xlabel("Time"); ax.set_ylabel("Signal")
        fig.savefig("case-06.png", dpi=300)
        fig.savefig("case-06.pdf")
        """,
    ),
    "case-07-inline-data": (
        "data inlined in the script, no source file",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        values = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3, 2, 3, 8, 4, 6, 2, 6, 4, 3, 3]
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(range(len(values)), values, "o-")
        ax.set_xlabel("Index"); ax.set_ylabel("Value (a.u.)")
        fig.savefig("case-07.png", dpi=300)
        fig.savefig("case-07.pdf")
        """,
    ),
    "case-08-literal-escape": (
        "a LaTeX escape rendered literally by matplotlib",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(np.linspace(0, 5, 20), rng.random(20), label="Leaf\\_type series")
        ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
        ax.legend()
        fig.savefig("case-08.png", dpi=300)
        fig.savefig("case-08.pdf")
        """,
    ),
    "case-09-text-over-line": (
        "an annotation sitting on top of the curve it annotates",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        x = np.linspace(0, 10, 100)
        fig, ax = plt.subplots(figsize=(3.5, 2.6))
        ax.plot(x, np.sin(x), linewidth=2.0)
        ax.text(5.05, -0.943, "on the curve", ha="center", va="center", fontsize=8)
        ax.set_xlabel("Time $t$ (s)"); ax.set_ylabel("Signal (V)")
        fig.savefig("case-09.png", dpi=300)
        fig.savefig("case-09.pdf")
        """,
    ),
    "case-10-open-seam": (
        "a matrix whose borders stop mid-air",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        fig = plt.figure(figsize=(3.5, 3.0))
        for i in range(3):
            for j in range(3):
                ax = fig.add_axes([0.1 + j * 0.28, 0.1 + i * 0.28, 0.26, 0.26])
                if i < j:
                    ax.axis("off")
                else:
                    ax.scatter(rng.random(8), rng.random(8), s=4)
                ax.set_xticks([]); ax.set_yticks([])
        fig.savefig("case-10.png", dpi=300)
        fig.savefig("case-10.pdf")
        """,
    ),
    "case-11-unbounded-matrix": (
        "a full matrix with every cell drawn, including the ones meant to be empty",
        """
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        plt.style.use([STYLE / "base.mplstyle"])
        rng = np.random.default_rng(0)
        fig = plt.figure(figsize=(3.5, 3.0))
        for i in range(4):
            for j in range(4):
                ax = fig.add_axes([0.08 + j * 0.23, 0.08 + i * 0.23, 0.21, 0.21])
                if i > j:
                    ax.scatter(rng.random(10), rng.random(10), s=3)
                ax.set_xticks([]); ax.set_yticks([])
                for side in ("top", "right", "bottom", "left"):
                    ax.spines[side].set_visible(True)
        fig.savefig("case-11.png", dpi=300)
        fig.savefig("case-11.pdf")
        """,
    ),
}

HEADER = '''# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Negative case: {description}

Planted defect — `sf_lint.py --all` must report it. This file exists so the lint has a
known-bad input; a linter with no failing fixtures is untested.
"""
from pathlib import Path
STYLE = Path(__file__).resolve().parents[2] / "styles"
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--outdir", default=".", help="where to write the case scripts")
    args = parser.parse_args()
    out = Path(args.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name, (description, body) in CASES.items():
        path = out / f"{name}.py"
        path.write_text(HEADER.format(description=description) + textwrap.dedent(body), encoding="utf-8")
        print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
