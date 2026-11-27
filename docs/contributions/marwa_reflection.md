# Reflection: Marwa Zeineddine (Data Acquisition Lead)

## My role

My job was to bring the data into the platform: everything after mine depends on it. If my part collects the wrong complaints, misses some, or changes a raw file, then Joseph's Spark job, the MongoDB load and the dashboard all show wrong numbers, and nobody downstream can see why. So I built the historical full load of the CFPB file (369,859,546 bytes, 19,397,176 records, checked with SHA-256 and never overwritten in `raw/`), the stratified sample, the incremental collector with its high-water mark, and the pipeline runner and scheduler. When the team chose Apache NiFi as the main collector on 23 November, I also built the NiFi flow that now runs every day at 02:00 UTC.

## The hardest part: building the NiFi flow

The hardest part for me was NiFi. I had never used it, and I had only a few days. In Python I could write a loop in three lines; in NiFi the same loop is a chain of processors and attributes: read the high-water mark from MinIO, prepare the run, call one page, save it, read its facts, count it, and decide if there are more pages. Every value is an expression, and one missing `$` in `run.ts` was enough to break the run ID. What made it click was understanding that a FlowFile carries its attributes from processor to processor, like the variables of my Python loop. After that I could reuse what I had already learned about the API in Python: the `python-requests` User-Agent that the firewall accepts, `search_after` instead of `frm`, and sending the end date plus one day.

The error side took me longer than the happy path. I tested it on purpose with a wrong URL. The server answered HTTP 200 with an HTML page, so my flow did not see an HTTP error, and the FlowFile ended in the funnel without any run log. I added a route from "Read page facts" to a failure branch, with the message "HTTP 200 but the response is not valid JSON". Now a failed run always leaves a run log that explains what happened.

## A decision I defend

The high-water mark only moves forward after Spark and the MongoDB load both succeed, and every run re-reads 21 days before it, with duplicates removed by complaint ID. I did not just accept this rule, I saw it work. On 27 November the successful NiFi run moved the mark from 2026-11-23 to 2026-11-25 after the 1,931 complaints were processed and loaded. Then my failed test run wrote `outcome: failed`, and the mark stayed at 2026-11-25. If the mark had moved, the complaints of that window would have been skipped forever. Collecting a few days twice costs nothing, because deduplication removes them.

## What I would do differently

What cost me the most was setup and waiting. The first installation took more than an hour, the Docker images were rebuilt several times, and the full ZIP was downloaded again after the build cache was lost and after I restarted my laptop. During those waits I could not test anything. Next time I would set up the environment and download the large file on the first day, keep a local copy of the file to work with, and work on the code and documentation while the long steps run, instead of waiting for them.

## What I learned

Before 17 November I had never built a data flow in NiFi or used Docker for real work. Now I can build a NiFi flow with loops, retries and error branches, use environment variables instead of hard-coded values, and export it without secrets so a teammate can import it. With Docker, I can start the platform, read the logs of a container, and fix problems such as a stale lock left by a stopped container. I also learned that the documentation of an API is not enough: you have to test how it really behaves and write down what you find, as I did in `docs/api_notes.md`.
