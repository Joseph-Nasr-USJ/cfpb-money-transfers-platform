<!--
Section 7. Reflection and next steps
Owner: Loutchiana (with Charbel) | Target: 250 words | First draft: Sat 21 Nov (status as of 21 Nov); update on Wed 25 Nov
from the contribution logs (docs/contributions/) and the checkpoint notes (docs/checkpoints/).
-->

## 7. Reflection and next steps

**Team process.** Six members each own a folder, so most Pull Requests touch different files. The `main` branch is protected: every change goes through a branch, a Pull Request and a review by a named teammate. Each member keeps a weekly contribution log and the lecturer's checkpoints are written up as short notes. Brief version 2 and the lecturer's request for course tools added NiFi, Redis and Spark MLlib late, so the plan, the contracts and the task files were revised in one day.

**Design trade-offs.** A daily batch rather than streaming, because the CFPB publishes daily; MongoDB for serving with Parquet in MinIO as the trusted source; the tested Python collector kept next to NiFi so the demonstration does not depend on one tool.

**Unresolved issues.** The NiFi flow is not exported to `ingestion/nifi/`, so the Python collector is the collection path the pipeline uses. The lecturer has not yet approved the legacy product labels, which account for 5,710 of the 205,271 curated complaints. The Spark merge and the MongoDB loader insert and update by `complaint_id` but never delete, so a complaint that the CFPB drops from its file stays in the curated data and in MongoDB.

**Next improvement.** A MongoDB replica set with automatic primary election and majority writes, so that losing one node no longer means rebuilding the database. Sharding is not needed at about 200,000 documents.

**What we would do differently.** [TO COMPLETE with Charbel after the rehearsals: one or two lessons about planning, integration and testing.]
