# develop-oncology-question

A Claude Code skill that coaches you to a good **oncology** research question. It extends the four-phase method of Peters (*Nat Hum Behav* 2025, https://doi.org/10.1038/s41562-025-02292-5) with oncology-specific evidence checks:

- **What is known**: PubMed, Europe PMC preprints, ASCO/ESMO/CSCO abstracts
- **Who is doing it** (collision check): ClinicalTrials.gov, ChiCTR, WHO ICTRP
- **Evidence gaps**: NCCN / CSCO / ESMO guideline recommendation levels
- **Biology & subgroup size**: cBioPortal / TCGA, CIViC, OncoKB, Open Targets
- **Feasibility**: GLOBOCAN, registries, and an enrollment estimate
- **Oncology traps**: me-too designs, unvalidated surrogate endpoints, biomarker-level confusion, outdated comparators

The skill text is in Chinese.

## Contents

- `SKILL.md`: the coaching workflow
- `references/oncology-databases.md`: a database map with API notes
- `scripts/onco_scan.py`: a one-command evidence-landscape scan (Python stdlib only)

```bash
python3 scripts/onco_scan.py --condition "gastric cancer" --intervention "zolbetuximab" \
  --gene ERBB2 --study stad_tcga_pan_can_atlas_2018 --civic-disease Stomach -o scan.md
```

Scan results give a rough picture only. Always verify against the original sources.

## Install

```bash
git clone https://github.com/qitong/develop-oncology-question ~/.claude/skills/develop-oncology-question
```
