# integrations/

This directory is where **donor repositories** are cloned for analysis and
selective feature harvesting. Miori Core is a *new* architecture — we do **not**
merge these repos wholesale. We study them, document them in
`docs/repo-analysis/`, and port specific patterns into the relevant Miori
module.

## Layout

| Folder | Donor | Harvest focus | Maps into |
| --- | --- | --- | --- |
| `mark-xlvi/` | Mark-XLVI / MARK family | remote dashboard, file transfer, wake/sleep, device control | `apps/remote-dashboard/`, `services/core-api/app/services/remote/` |
| `odysseus/` | Odysseus workspace | workspace IA, provider flexibility, memory/skills | `apps/desktop/src/features/`, `services/core-api/app/services/providers/`, `.../memory/` |
| `khoj/` | Khoj second-brain | semantic retrieval, knowledge indexing, automations | `services/core-api/app/services/memory/`, `.../tasks/` |
| `future/` | placeholder | computer-use, orchestration, voice donors added later | `services/core-api/app/services/tools/` |

## Workflow

1. Clone a donor repo into its folder, e.g. `git clone <url> integrations/odysseus`.
   (These clones are **git-ignored** content-wise except for the placeholder docs.)
2. Run `python scripts/analyze_repos.py` to generate a mechanical stack inventory.
3. Write/expand the human analysis in `docs/repo-analysis/<repo>.md`.
4. Port specific patterns per the mapping in `docs/feature-matrix.md`.

> Licensing: respect each donor repo's license when porting code. Prefer
> re-implementing patterns over copying files; record provenance in the relevant
> module's header comment.
