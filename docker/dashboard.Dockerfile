
FROM python:3.11-slim

WORKDIR /app

COPY requirements-dashboard.txt .

RUN pip install --no-cache-dir -r requirements-dashboard.txt

COPY dashboard/ ./dashboard/
COPY database/ ./database/

# Make /app available for Python imports
ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
