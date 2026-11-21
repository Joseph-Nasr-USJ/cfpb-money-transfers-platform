# Contribution log: Loutchiana Marie

Role: Delivery lead (technical report, architecture and data documentation, dashboard content, presentation). Updated every Sunday.

## Week of Mon 16 to Sun 22 Nov 2026

**Date:** Sat 21 Nov 2026

**What I did**
- Read the brief V2, the four course sessions, my task file and the task files of my teammates, then read the repository: the Docker stack, the Spark job, the quality gate, the MongoDB model and queries, the metric definitions, the README, runbook, test plan and demo script, and Marwa's collector branch.
- Cloned the repository outside OneDrive (`C:\Dev\`), set my Git identity for this repository only and worked on branches named `loutchiana/<topic>`.
- Wrote the technical report skeleton with the 14 section files (owners, word targets, deadlines) and a small script that assembles the report and counts the words per section (`docs/report/`).
- Wrote report section 2 (problem and scope), section 3 (data source, limitations, responsible use and ethics) and section 4.1 (architecture); drafted section 1 (executive summary, findings to be added), section 7 (reflection and next steps) and the section 8 reference list with the appendix index.
- Wrote the architecture document with the diagram (PNG and Mermaid), the purpose of the seven layers, the technology chosen and the alternative considered, the trade-offs and the MinIO decision (`docs/architecture.md`).
- Wrote the data dictionary: every curated field, the product mapping and state reference list, the aggregates, the quarantine, quality report, manifest and run log (`docs/data_dictionary.md`).
- Wrote the dashboard texts: overview, measure definitions, limitations and cautions (`dashboard/content/`), consistent with Perla's `docs/metrics.md`.
- Wrote the checkpoint notes of 13 and 20 November from the repository history (`docs/checkpoints/`).
- Wrote the slides outline, the script of my demo step 1 and the likely questions on the architecture (`docs/presentation/slides_outline.md`).
- Checked the CFPB statements used in the report against the official pages and release notes (accessed 21 Nov), and Marwa's API notes (licence CC0, 199,152 records for the current label).
- Used an AI assistant (Claude Code) to draft these documents from the repository and the official sources; I review the content and must be able to explain it.

**Pull Requests**
- One Pull Request from branch `loutchiana/delivery-docs` with all of the above: report skeleton and sections, architecture document, data dictionary, dashboard texts, slides outline and this log. Reviewed and merged by Joseph.

**Problems**
- I started late: the report skeleton and section 2 were due on Sat 14 Nov, and the architecture document, data dictionary and dashboard texts on Wed 18 Nov. Perla and the others could not use my texts before today.
- My teammates' task files describe the earlier plan (no Redis in Perla's, a nine-step demo in Charbel's). I followed my own updated file and the code on `main`.
- The repository differs from the shared contract in two places: the Spark job writes `curated/complaints/domain=money_transfers_payments/` while the contract and the MongoDB loader use `option=5`; and `processing/quality.py` still calls two dimensions `timeliness` and `integrity`, while brief V2 names them freshness and reconciliation. Both are written in `docs/architecture.md` (section 12) and must be settled with Joseph and Christopher.
- The `nifi` and `redis` services and Marwa's collectors are not on `main` yet, so the architecture document marks them as target.
- `make` is not installed on my machine yet and I have not run `make up` or `make test` myself.
- The checkpoint notes are based on the repository history; I still have to check them with the team.

**Next step**
- Install `make`, run `make up` and `make test`, and check the MinIO console.
- Open the Pull Requests above for review by Charbel and tell the team where their report section files are (deadline Wed 25 Nov).
- Agree the two contract differences with Joseph and Christopher, and the Redis decision with Perla.
- Collect screenshots (MinIO, MongoDB Compass, dashboard, quality report) into `docs/images/` as they exist.
- Update the executive summary, section 7 and the appendices when `docs/findings.md` (Tue 24 Nov) and the evidence files exist.
