# Individual reflection: Joseph Nasr

Role: Data Engineering Lead and Repository Integrator. Group 5, option 5, Money Transfers and Digital Payments.

## What I was responsible for

I built the foundation the others worked on: the Docker stack, the Spark job and the quality gate. I was also the integrator: I reviewed and merged almost every Pull Request and kept the shared files and the contracts between components consistent. The second role turned out to be at least as much work as the first.

## What went well

The decision that paid off most was to agree on contracts early: one run_id format, fixed raw paths, one run log, one curated path. Because the collector, the Spark job and the loader only depended on these contracts, Marwa, Christopher and I could work in parallel, and the pieces fitted together the first time we ran them on real data. When the brief changed the curated path to `option=5/year=YYYY/month=MM`, I moved the path into one shared module, so the Spark job, the loader and the ML scripts could never point at different folders again.

The quality gate also proved its value. Writing the thresholds before seeing any result forced me to decide what a failure means, and the deliberate bad records in the test fixtures showed that the gate stops a bad run instead of publishing it. On the full file of 19,397,176 records, the counts reconciled exactly and three machines produced identical results.

## What was difficult

Integration was harder than coding. Several problems only appeared when components met: a NiFi health check that could never pass because NiFi listens on the container hostname, a Spark rerun that had to merge rather than append, a MongoDB total that keeps growing once the scheduler runs, so the report needs a fixed snapshot. None of these showed up in unit tests; they appeared only when I ran the whole chain.

Reviewing was the other difficulty. Teammates worked at different speeds and sometimes opened Pull Requests based on an old version of main, or several small ones at once. I learned to check each branch merged with the current main before approving, and to test what would actually be merged rather than the branch alone.

I also made a mistake of my own: my office PC had a mistyped email address in its Git configuration, so GitHub does not credit about thirty of my commits to my account. It changed nothing in the code, but it taught me to check the basics of a new machine before the first commit.

## What I would do differently

I would run the full historical load much earlier. The real data changed several decisions: no complaint in our domain has a sub-issue, about 5% have no state, and volume in 2025 is about five times that of 2024. Knowing this in the first week would have shaped the quality rules, the aggregations and the findings sooner. I would also start the NiFi flow at the same time as the Python collector instead of after it, because it is the part of collection the course asked for and it remained the last open piece.

## Use of AI

I used an AI assistant (Claude) as a mentor and pair-programmer: to explain concepts, draft code, tests and documents, and review teammates' Pull Requests. I checked every output by running the tests and the pipeline on real data before merging, and I am responsible for everything I merged.

## What I take away

A data platform is mostly agreements: about paths, formats, names and what counts as a failure. The code that respects those agreements is the easier half. I now understand why lineage, idempotent reruns and explicit quality thresholds matter more than any single transformation: they are what make a result trustworthy enough to show to someone else.
