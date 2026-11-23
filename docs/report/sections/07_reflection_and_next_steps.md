<!--
Section 7. Reflection and next steps
Owner: Loutchiana (with Charbel) | Target: 250 words | First draft: Sat 21 Nov (status as of 21 Nov); update on Wed 25 Nov
from the contribution logs (docs/contributions/) and the checkpoint notes (docs/checkpoints/).
-->

## 7. Reflection and next steps

**Team process.** Six members each own a folder, so most Pull Requests touch different files. The `main` branch is protected: every change goes through a branch, a Pull Request and a review by a named teammate, merged with a merge commit. Each member keeps a weekly contribution log, and the lecturer's checkpoints were written up as short notes. The brief was updated during the project (version 2) and the lecturer asked for course tools, so NiFi, Redis and Spark MLlib were added late; the shared plan, the contracts and the task files had to be revised in one day.

**Design trade-offs.** We chose a daily batch over streaming, because the CFPB publishes daily and the brief rules streaming out. We chose MongoDB as the serving store and kept Parquet in MinIO as the trusted source. We kept the tested Python collector next to NiFi so that the demonstration does not depend on one tool. MinIO no longer publishes official images, so we pinned a community rebuild.

**Unresolved issues.** [TO COMPLETE on Wed 25 Nov from the repository: for example whether NiFi and Redis are merged and verified, the curated path `option=5`, the quality dimension names of brief V2, the approval of the legacy product labels, and any open defect.]

**Next improvement.** The improvement to prioritise is a MongoDB replica set with automatic primary election, majority writes and reads from the primary, so that the loss of one node no longer means rebuilding the database. Sharding is not needed at about 200,000 documents. After that, a Spark cluster would be needed only if the data grew by orders of magnitude.

**What we would do differently.** [TO COMPLETE with Charbel after the rehearsals: one or two lessons about planning, integration and testing.]
