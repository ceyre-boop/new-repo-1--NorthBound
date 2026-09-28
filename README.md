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
- `python scripts/spec_checklist.py specs/fenwick-plumbing.spec.yaml --allow-empty-slots`

This shape keeps Fenwick simple, and still holds for Lakeside-style messy inputs without changing the assembly model.
