# Phase 3.17 Repair Taxonomy Check

Status: pending

Human labels are not complete; fill the 24-row template before evaluation.

## Teacher-Facing Files

- `docs/phase3_17_human_review_instructions.md`
- `data/manual/phase3_17_human_pack_24.blind.jsonl`
- `data/manual/phase3_17_human_template_24.csv`
- `data/manual/phase3_17_human_template_24.jsonl`

## Private Files

Do not send these to reviewers:

- `data/manual/phase3_17_human_analysis_private.jsonl`
- `data/manual/phase3_17_human_manifest.json`

## Next Command

After labels are returned, write them to `data/manual/phase3_17_human_labels_24.jsonl` or pass the filled CSV via `--labels`, then run:

```bash
python3 -m src.audit.eval_manual_taxonomy_check
```
