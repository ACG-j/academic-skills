# Evaluations

Two independent things are tested here. Neither runs automatically — both are checks a
maintainer runs after changing the skill.

## 1. Does the lint actually catch defects?

`negative-cases/` holds figures with planted defects. A linter that reports nothing looks
exactly like a linter that works, unless there are known-bad inputs it must flag.

```bash
cd negative-cases
uv run make_cases.py -o .                 # (re)generate the cases
for f in case-*.py; do
  uv run ../../scripts/sf_lint.py --all "$f" --json | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print('$f', d['ok'], [f['check'] for f in d['findings'] if f['severity']=='error'])"
done
```

| Case | Planted defect | Expected finding |
|---|---|---|
| `case-01-jet-colormap` | jet on continuous data | L1 `colormap` error |
| `case-02-tiny-font` | 4 pt text | L2 `font-size` error |
| `case-03-legend-over-data` | legend over the series | L2 `legend-overlap` warn |
| `case-04-no-vector` | PNG only, 72 dpi | L1 `export` error |
| `case-05-truncated-bar` | bar chart with nonzero baseline | L1 `truncated-axis` warn |
| `case-06-no-units` | labels without units | L1 `units` error |
| `case-07-inline-data` | 26 values inline, no seed | L1 `inline-data` + `data-source` errors |
| `case-08-literal-escape` | `Leaf\\_type` outside mathtext | L2 `literal-escape` error |
| `case-09-text-over-line` | annotation centred on its own curve | L2 `text-over-line` warn |
| `case-10-open-seam` | matrix cells switched off with `axis("off")` | L2 `open-seam` warn |

A positive control matters as much: a correct figure must come back clean. Without it,
"everything fails" would pass the suite.

## 2. Does the description trigger on the right requests?

`trigger-eval.json` holds 20 requests: 10 that should load this skill, 10 near-misses that
share vocabulary (`plot`, `chart`, `figure`, `TikZ`, `dpi`) but need something else — an
animation, a dashboard, a map, a format conversion, an opinion.

The negatives are the useful half. A description that fires on "convert this PNG to 600 dpi"
is too broad and will load 200 lines of review protocol for a one-line task.

There is no automated harness for this. Use it as a checklist when editing the
`description` field: read each query, ask whether the skill should load, and compare.

## Known limits

- The runtime layer executes the script. On an untrusted script, run the static layer only.
- L2 cannot see anything that depends on data distribution — that is the visual review's job.
- Negative cases cover the mechanical checks, not the judgement questions in `qa.md`.
