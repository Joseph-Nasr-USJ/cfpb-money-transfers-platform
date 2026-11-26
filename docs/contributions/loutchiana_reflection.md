# Individual reflection: Loutchiana Marie

Role: delivery lead (technical report, architecture and data documentation, dashboard texts, presentation). Group 5, option 5, Money Transfers and Digital Payments.

## What I was asked to do and how it went

My part was to document the platform so that the team, the professor and a reader who has never seen it can understand it: the technical report, the architecture document, the data dictionary, the dashboard texts and the slides. At the beginning I thought this was the easy part, because it seemed to be only writing. I changed my mind when I started. To describe a layer honestly I had to read the Docker stack, the Spark job, the quality gate and the loader.

I started late. The report skeleton and section 2 were due on 14 November, and the architecture document, the data dictionary and the dashboard texts on 18 November. I delivered most of it on 21 November, so Perla and the others could not use my texts earlier. Next time I will start with the code and the data, and write the skeleton second. Writing for several readers also meant checking every number twice, once against the quality report and once against the dashboard.

## What I learned technically

Writing the architecture made the course concepts concrete. I had to justify each choice against the alternatives: batch against streaming because the CFPB publishes daily; Parquet against CSV and ORC for columnar storage; MongoDB as the serving store because complaints are documents filtered on several fields.

I also ran the chain myself on the real file, on 22 and 24 November. The file of 24 November has 19,397,176 records; Spark keeps 205,271 in our domain, quarantines 112 and removes no duplicates, and the counts add up exactly. The runs showed me what the documents had not: Docker's default 2 GB is not enough for Spark, and our two counts, 199,152 from the API and 205,271 in the full load, measure different things.

The second run stopped at the MongoDB count check, with 205,272 documents for 205,271 curated. I first explained it as a gap in the loader and wrote that in the documents, and it was merged. Reading the Spark job showed the real cause: the curated data had moved from `domain=` to `option=5`, so Spark built the new folder from scratch while MongoDB still held a complaint from the load of 22 November that the CFPB had since dropped. I corrected the documents and added to the report that neither the Spark merge nor the loader deletes a complaint the CFPB drops, so the next reader does not meet the same surprise. The lesson is to find the cause before writing it down.

## What I learned about teamwork

My biggest mistake was a process one. I opened seven small Pull Requests with reviewers, which sent many notifications to Joseph and Charbel before I had agreed anything with them. I closed them, kept one Pull Request, and Joseph merged it. Now I decide with the team how many Pull Requests there will be, and who reviews them, before opening any.

I also learned to compare the documents with the code and not with the plan. The code on `main` differed from the shared contract in two places, the curated path and the names of two quality dimensions. I wrote these differences in the architecture document instead of hiding them, Joseph closed both on 24 November, and I updated the documents.

## Limits and what is still open

The data is a set of complaints, not a random sample, with no confirmed fraud and no transaction denominators. The report and the dashboard therefore describe and compare; they do not rank companies, explain causes or forecast. The dashboard now shows my texts, and I changed two of them after the data showed that no complaint in the domain has a sub-issue and that about 5% have no state.

Still open at the time of writing: the NiFi flow is not exported, so the Python collector is the working path; the lecturer has not approved the legacy product labels; and the findings and some report sections were still waiting to be merged.

## Next improvement

For the platform, a MongoDB replica set and a scheduled run with the exported NiFi flow. For myself, an earlier start and a shared checklist of deadlines for the section owners.
