# Agent teams

Multi-figure work parallelizes badly if everyone edits the same files, and reviews badly if
the author reviews their own figure. This file describes how to split figure work across
agents without either problem.

**Default: don't use a team.** One agent doing contract → implement → review → export is
faster than coordinating three. Reach for a team when the work is genuinely parallel (many
figures) or when independent review is the point.

---

## When to use a team

| Situation | Configuration |
|---|---|
| One figure, quick turnaround | no team — the lead does it |
| One figure, publication-bound | lead + one independent critic |
| 2–4 figures | lead + one implementer per figure + one shared critic |
| 5+ figures | lead + implementer pool + two critics (different rounds) |
| Mixed stacks (data + schematic + table) | one owner per stack |
| Existing figures need auditing | lead + one auditor per batch, no implementers |

---

## Roles

| Role | Writes to | Does | Never does |
|---|---|---|---|
| **Lead** | `contracts/` | writes the contract, splits the work, arbitrates severity, delivers | edits figure source |
| **Implementer** | `figs/<fig>/` | writes the script, runs lint, fixes findings | reviews its own figure |
| **Critic** | `qa/<fig>/` | crops, inspects, writes the finding table | edits the figure |
| **Exporter** | `out/<fig>/` | exports, verifies fonts, compiles TikZ, writes the manifest | changes the figure |

The separation is the point. An implementer reviewing its own figure finds what it expected
to find. A critic that can also edit will "fix" things it has not diagnosed.

**Write scopes must be disjoint.** Two agents writing `figs/fig2/` will clobber each other;
the filesystem will not stop them.

---

## Task graph

```
contract ──> implement ──> lint ──> review-r1 ──> fix ──> review-r2 ──> export ──> accept
```

Dependencies that matter:

- `implement` is blocked by `contract` — without a claim the figure has no target
- `review-r1` is blocked by `lint` — reviewing a figure that fails static checks wastes the
  critic's attention on defects a machine already found
- `fix` is blocked by `review-r1` — never fix what has not been diagnosed
- `review-r2` is blocked by `fix` — and it starts with a diff, not a fresh look
- `export` is blocked by `review-r2` — exporting an unreviewed figure means re-exporting later

Per figure, in parallel across figures. The only true barrier is the final delivery.

---

## Handoffs

Every handoff carries the same four things, or the receiver guesses:

1. **The artifact path** — the script, the render, the crop directory
2. **The contract** — what the figure must claim
3. **What was already checked** — so the critic does not redo lint
4. **What is unresolved** — open findings, accepted warnings, and why

```
fig2 ready for review.
  source:   figs/fig2/plot.py
  render:   figs/fig2/fig2.png (925x692, 300 dpi)
  contract: contracts/fig2.yaml — claim: sorted allocation wins above 60% load
  lint:     L1+L2 clean after 2 fixes (jet colormap, legend overlap)
  open:     none; accepted warning: dual axis justified, physical link stated
  target:   nature single column, 89 mm
```

A critic receiving "please review fig2" will review the wrong things.

---

## Critic protocol

The critic is the one who makes the review real. Its rules:

1. **Overlay first.** `sf_crop.py --overlay` then read coordinates. Never estimate.
2. **Crop what matters**, not a uniform grid — text, legend, annotations, dense regions.
3. **Record findings in the table format** with region, defect, severity, evidence, fix.
4. **Evidence is mandatory.** "crop 02-y-label shows `-0.5` with a hyphen" — not "the minus
   sign looks odd".
5. **Do not edit the figure.** The finding goes to the implementer.
6. **Calibrate severity** per `qa.md`. Inflated severity makes the review ignorable;
   deflated severity ships defects.

The critic's output is a table plus a verdict: blocking findings count, and whether the
figure clears the four judgement questions.

---

## Arbitrating disagreement

The implementer will sometimes disagree with a finding. The resolution path:

- **Is it reproducible?** Look at the crop. If the crop does not show it, the finding is
  wrong (often a bad crop box).
- **Is it a defect or a preference?** Missing unit = defect. "I'd use a different blue" =
  preference. Preferences are recorded as accepted, not argued.
- **Does the contract settle it?** If the contract says the claim is X and the figure shows
  Y, that is a defect regardless of who is right about aesthetics.

The lead decides, and the decision is recorded with a reason — the next round should not
re-litigate it.

---

## Task board shape

`templates/team-plan.yaml` is a starting point:

```yaml
figures:
  - id: fig2
    contract: contracts/fig2.yaml
    implementer: plotter-1
    scope: figs/fig2/
  - id: fig3
    contract: contracts/fig3.yaml
    implementer: plotter-2
    scope: figs/fig3/

reviewers:
  - id: critic
    scope: qa/
    rounds: [1, 2]

export:
  owner: exporter
  scope: out/
```

Scopes are advisory, not enforced. Two agents in the same directory is a coordination bug,
not a lock contention — check the scopes before spawning.

---

## Cost note

Each agent re-reads the context it needs. For a single figure, a team costs more than it
saves: three agents each need the contract, the style, and the conventions. Use a team when
the parallel work exceeds that overhead — which for figures means roughly three or more
figures, or when independent review genuinely requires a separate perspective.
