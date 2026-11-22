# Individual reflection: Loutchiana Marie

Role: delivery lead (technical report, architecture and data documentation, dashboard texts, presentation). Group 5, option 5, Money Transfers and Digital Payments.

## What I was asked to do and how it went

My part was to document the platform so that the team, the professor and a reader who has never seen it can understand it: the technical report, the architecture document, the data dictionary, the dashboard texts and the slides. At the beginning I thought this was the easy part, because it seemed to be only writing. I changed my mind when I started. To describe a layer honestly I had to read the Docker stack, the Spark job, the quality gate and the MongoDB loader, and to decide what each one was for.

I started late. The report skeleton and section 2 were due on 14 November, and the architecture document, the data dictionary and the dashboard texts on 18 November. I delivered most of it on 21 November, so Perla and the others could not use my texts earlier. I could have asked for the repository access and read the code in the first week instead of waiting. Next time I will start with the code and the data, and write the skeleton second.

## What I learned technically

Writing the architecture made the course concepts concrete. I had to justify each choice against the alternatives: batch against streaming because the CFPB publishes daily; Parquet against CSV and ORC for columnar storage and compression; MongoDB as the serving store because complaints are documents filtered on several fields; a single node, so the CAP trade-off does not arise yet, and a replica set as the first improvement. MinIO was a good example of a real constraint: the official image can no longer be pulled, so we pin a community rebuild to an exact tag.

I also ran the chain myself on the real file. The CFPB file has 19,371,701 records; the Spark job keeps 205,064 in our domain, quarantines 112 and removes no duplicates, and the counts add up exactly. The same run showed me two things the documents had not: Docker's default 2 GB of memory is not enough for Spark, and our two record counts, 199,152 from the API and 205,064 in the full load, measure different things (the current product label against the current and the legacy labels). I now explain both in the report.

## What I learned about teamwork

My biggest mistake was a process one. I used an AI assistant to prepare my work, and it opened seven small Pull Requests with reviewers, which sent many notifications to Joseph and Charbel before I had agreed anything with them. I closed them, kept one Pull Request, and Joseph merged it. The lesson is to decide with the team how many Pull Requests there will be, who reviews them and when, before opening any.
I also learned to compare the documents with the code and not with the plan. The task files of my teammates described an earlier plan, and the code on `main` differed from the contract in places (the curated path, the names of two quality dimensions). I wrote these differences in the architecture document so the team can settle them, instead of hiding them.

## Limits and what is still open

The data is a set of complaints, not a random sample, and it contains no confirmed fraud and no transaction denominators. The report and the dashboard therefore describe and compare; they do not rank companies, explain causes or forecast.
Still open at the time of writing: the NiFi flow is not exported, the dashboard is on Perla's branch and does not use my texts yet, the findings are not final, and the two contract differences need an agreement with Joseph and Christopher.

## Next improvement

For the platform, a MongoDB replica set and a scheduled run with the exported NiFi flow. For myself, an earlier start and a shared checklist of deadlines for the section owners.

## Use of AI

I used an AI assistant (Claude Code) to read the repository and the official sources and to draft the documents, the slides and the first version of this text from my contribution logs. I checked the content, ran the platform myself, and I am responsible for what I submit.
