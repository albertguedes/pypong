#
# Django Dockerfile
#
FROM python:3.13-alpine

RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D appuser

RUN apk add --no-cache \
    postgresql-client \
    libpq \
    curl

WORKDIR /var/www

COPY --chown=appuser:appgroup requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8001

ENV POSTGRES_HOST=127.0.0.1
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=dockerdb
ENV POSTGRES_USER=docker

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--threads", "4", "myproject.wsgi:application"]