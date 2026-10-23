# artisan-companion (working title)

A companion app for [Artisan](https://artisan-scope.org/) scope users who log their
coffee roasts as `.alog` files and want to attach **sensory information** (cupping
notes, flavor scores, defects) to each roast, and to **review roast profiles**
(curves, events, phases) without opening Artisan.

> Status: M1 alog_core parser, M2a sensory store, M2b sensory editor web app implemented on branch dev; 167+ tests; CI via GitHub Actions.

## Goals

1. **Sensory annotation** — add structured sensory data (SCA-style cupping scores,
   aroma descriptors, defects, brew impressions) to existing Artisan `.alog` roast
   logs, in a way that is safe for the original files and, where possible, visible
   inside Artisan itself.
2. **Profile viewer** — render a roast profile (ET/BT curves, RoR, event markers,
   phase boundaries) from a `.alog` file, similar to what Artisan shows, but as a
   lightweight standalone viewer with the sensory data displayed alongside.

## Scope

The app works **offline on existing `.alog` files**, long after the roast
happened — sensory impressions arrive days or weeks later, once beans are
rested and cupped, which is exactly the information that cannot be captured in
Artisan during a roast or shortly after. It deliberately does **not**:

- interface with Artisan while it runs (no live telemetry, no recording,
  no daemon, no plugin or messaging connection);
- replace any part of Artisan's logging workflow.

Artisan only ever re-encounters the data indirectly: when the user opens an
annotated log in Artisan, the sensory summary written to the native fields is
visible there like any data entered in Artisan itself.

## Documentation

| Document | Content |
|---|---|
| [docs/feasibility-evaluation.md](docs/feasibility-evaluation.md) | What the `.alog` format allows, what survives a round trip through Artisan, and the verdict |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Architecture, data model, tech stack, milestones, risks |
| [docs/ui-spec.md](docs/ui-spec.md) | Proposed UI specification: screens, wireframes, states, acceptance criteria |
| [research/upstream-findings.md](research/upstream-findings.md) | Evidence collected from the Artisan source code and a 230-file log corpus |

## Context

The evaluation was performed against a real corpus of 230 `.alog` files
(2021–2026, Artisan versions 2.4.6 → 4.2.0) and the open-source Artisan code base
(https://github.com/artisan-roaster-scope/artisan). Format analysis details are in
that evidence file and in the pre-existing technical descriptions of the corpus.

## License

MIT (pyproject.toml declares license = { text = "MIT" }).
