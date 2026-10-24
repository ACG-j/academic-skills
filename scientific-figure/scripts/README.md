# Scripts

All scripts are PEP 723 self-declaring: the dependencies are in the file header, and
`uv run script.py` builds an isolated environment on first use. Nothing needs installing
into the system Python.

## Conventions

- **JSON on stdout**, human summary on stderr. Machine-readable output means an agent can
  parse results without regexing prose.
- **Exit code 0 = nothing blocking, 1 = blocking finding, 2 = usage error.** So a script can
  gate a pipeline.
- **No hidden state.** Each invocation is independent; none of them write to a shared config.
- **Missing tools degrade, they do not crash.** If `pdffonts` is absent, the PDF check reports
  that it could not verify fonts rather than failing the run.

## Order of use

```
sf_doctor.py      → can this machine do the work?
sf_init.py        → scaffold the project and the contract
sf_style.py       → pick or build a style
sf_palette.py     → audit the colours
  (write the figure)
sf_lint.py        → static, then runtime
sf_crop.py        → overlay, then crop what you chose
sf_diff.py        → what changed between rounds
sf_export.py      → export and verify
sf_tex2png.py     → for the TikZ route
sf_table.py       → for tables
sf_sheet.py       → many figures on one page
```

## Quick reference

| Script | Key flags |
|---|---|
| `sf_doctor.py` | `--fix` to print repair commands |
| `sf_init.py` | `--style --backend --claim --width-mm` |
| `sf_style.py` | `--list --show --apply --preview --from-spec` |
| `sf_palette.py` | `--list --audit --background --strict` |
| `sf_lint.py` | `--static --run --image --all` |
| `sf_crop.py` | `--overlay --spec --box --auto --zoom` |
| `sf_diff.py` | `--before --after --threshold` |
| `sf_export.py` | `--script --inspect --target-mm --snippet` |
| `sf_tex2png.py` | `--engine --dpi --no-crop` |
| `sf_table.py` | `--style --best-max --best-min --notes` |
| `sf_sheet.py` | `--images --dir --cols --cell` |

## Testing

The scripts have known-bad fixtures in `../evals/negative-cases/`. See
`../evals/README.md`.

## Dependencies and the runtime layer

`sf_lint.py --run` and `sf_export.py --script` execute the target script **in their own
process**, so the script's third-party imports must already be importable. Their PEP 723
headers cover the common case (`matplotlib`, `numpy`, `pillow`), but a script that imports
`pandas`, `seaborn`, `scipy`, or anything else needs those added:

```bash
uv run --with pandas --with scipy <script> ...
```

Both tools pre-flight the target's imports and report the exact missing module with that
command, instead of surfacing a `ModuleNotFoundError` traceback from inside user code.
`--static` never executes anything, so it always works.
