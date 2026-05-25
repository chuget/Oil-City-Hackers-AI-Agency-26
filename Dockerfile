# ProcureIntel HTML dashboard (monitor_site) — parallel to Amplify web/ deploy
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor_core.py monitor_charts.py monitor_dashboard.py monitor_chat.py ./
COPY monitor_site/ ./monitor_site/
COPY data/ ./data/

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')" || exit 1

CMD ["python", "-m", "uvicorn", "monitor_site.server:app", "--host", "0.0.0.0", "--port", "8765"]
