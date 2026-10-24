# Examples

Each example is a complete figure with its source, its data, and its review record — not a
screenshot. The point is that the whole path is reproducible: run the script, get the same
figure, see what the review found.

## `fig1-timeseries-ci/`

The reference example. A time series with a confidence band, Nature single-column sizing,
Chinese-free but with a deliberate review finding.

| File | What it is |
|---|---|
| `plot.py` | the plotting script, PEP 723 self-declaring |
| `contract.yaml` | the claim, panels, target, stats |
| `fig1.png` | review render at 300 dpi |
| `fig1.pdf` | vector output, fonts embedded |
| `review.md` | the finding table from both review rounds |

The review found a real defect that static analysis cannot see: `axes.unicode_minus = False`
in an early version of the base style rendered `-0.5` with a hyphen instead of a minus sign.
The crop at `qa/r1/01-ylabel.png` showed it; the fix and the diff are recorded in
`review.md`.

## Running an example

```bash
cd examples/fig1-timeseries-ci
uv run plot.py

# lint
uv run ../../scripts/sf_lint.py --all plot.py

# review: overlay first, then crop what you chose
uv run ../../scripts/sf_crop.py --image fig1.png --overlay -o qa/
uv run ../../scripts/sf_crop.py --image fig1.png --spec qa/crops.json -o qa/r1

# export and verify
uv run ../../scripts/sf_export.py --inspect . --target-mm 89
```

## What the examples are not

They are not a style gallery. A gallery of pretty figures teaches nothing about whether the
axes are honest, the units are present, or the legend covers the data. The examples show the
process, including the defects it caught.
