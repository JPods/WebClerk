FROM python:3.13

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=webclerk3_api.settings

CMD ["celery", "-A", "webclerk3_api", "worker", "-l", "info"]