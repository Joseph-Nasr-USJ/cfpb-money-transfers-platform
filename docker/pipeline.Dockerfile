# Pipeline image: Python 3.11 + Java 17 + PySpark 3.5 (local mode) + S3A jars for MinIO.
# Runs the collectors, the Spark job, the MongoDB loader and the scheduler.
#
# Debian 12 "bookworm" is pinned on purpose: the plain python:3.11-slim tag now uses Debian 13,
# which no longer ships Java 17, and Spark 3.5 does not support Java 21.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Java 17 for Spark; procps because Spark's launch scripts call `ps`; curl to download the jars.
# JAVA_HOME points to a fixed symlink so the same file works on Intel (amd64) and Apple Silicon (arm64).
RUN mkdir -p /usr/share/man/man1 \
 && apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")" /opt/java
ENV JAVA_HOME=/opt/java

WORKDIR /app

# Python dependencies (pinned versions)
COPY requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN pip install -r /tmp/requirements-pipeline.txt

# S3A connector so Spark can read and write s3a://cfpb-lake/... on MinIO, downloaded at build time
# so the container never downloads anything at runtime.
# Versions must match the Hadoop bundled in PySpark 3.5.9: Hadoop 3.3.4 -> aws-java-sdk-bundle 1.12.262.
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_BUNDLE_VERSION=1.12.262
RUN SPARK_JARS="$(python -c 'import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), "jars"))')" \
 && curl -fsSL -o "$SPARK_JARS/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
      "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar" \
      "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar" \
 && ls -l "$SPARK_JARS" | grep -E "hadoop-aws|aws-java-sdk-bundle"

# The repository code is not copied in: docker-compose.yml mounts the repository at /app,
# so code changes are picked up without rebuilding the image.
CMD ["python", "-m", "ingestion.scheduler"]
