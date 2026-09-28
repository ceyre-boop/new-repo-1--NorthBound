# new-repo-1--NorthBound
This repo captures how to move from an idea to a fully assembled system.

## Site spec contract
The canonical intake/build contract is now in:
- `spec.schema.yaml`

Per-client specs live under:
- `specs/`

Included examples:
- `specs/fenwick-plumbing.spec.yaml` (clean baseline)
- `specs/lakeside-messy.spec.yaml` (messy intake variant)

## What was missing from the draft and now captured
- **Typed validation contract** (required top-level blocks, constrained section types)
- **Asset readiness tracking** (`have|need|replace|rejected`)
- **Page-level SEO override support** (partial overrides allowed per page) while keeping global SEO required
- **Round-cap/go-live constraints** so review limits are encoded in the spec

## Intake checklist validator
Use `scripts/spec_checklist.py` to enforce intake completeness and cross-references:
- validates required top-level blocks
- validates structural shapes for `pages`, `sections`, `copy`, `images`, and `seo`
- ensures section image references exist in `images`
- ensures global/page `seo.og_image` references exist in `images`
- flags empty copy and alt slots as unresolved work orders (rejected images are exempt from alt completion)

Example:
- `python scripts/spec_checklist.py specs/fenwick-plumbing.spec.yaml --allow-empty-copy-slots` (suppresses empty copy slots only)

This shape keeps Fenwick simple, and still holds for Lakeside-style messy inputs without changing the assembly model.

## Northbound Ops Ledger (Stages 4·5·6)
Ops baseline and targets live in:
- `ops-ledger.stages-4-5-6.yaml`

Practice-run log schema (one row per step, per run):
- `run_id,step_id,started,stopped,wall_min,hands_min,brain_0_5,type_I_M_A_W,blocker,what_would_have_deleted_this_step`

Template and baseline log:
- `ops/logs/template.csv`
- `ops/logs/run-a.baseline.csv`

Generate the ledger report:
- `python scripts/ops_ledger_report.py`
- default discovery includes `ops/logs/run-*.csv` (excluding `*.baseline.csv`) plus `ops/logs/run-*.baseline.csv`
- discovered log rows must be unique by `(run_id, step_id)` across files

The report computes:
- HANDS/WALL ratio
- BM totals and I/M/A/W BM shares
- pass/fail vs targets
- BM × frequency kill-order ranking

Current operating sequence encoded in the ledger:
- harden 5 → instrument 4 → fence 6
