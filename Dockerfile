FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home setu
COPY bot ./bot
COPY web ./web
RUN mkdir -p /app/data && chown -R setu:setu /app
USER setu
ENV PORT=8000 DATABASE_PATH=/app/data/setu.db APP_ENV=production
EXPOSE 8000
CMD ["python", "-m", "bot.app"]
