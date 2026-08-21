FROM python:3.12-slim-bookworm

WORKDIR /app

# Driver ODBC SQL Server (pour l'ingestion SAGE X3)
# Contournement Fastly 403 : deb.debian.org renvoie 403 au User-Agent d'apt
# (Debian APT-HTTP/1.3) alors que curl/wget passent en 200. On force un UA curl.
RUN printf 'Acquire::http::User-Agent "curl/8.5.0";\nAcquire::https::User-Agent "curl/8.5.0";\n' \
        > /etc/apt/apt.conf.d/99useragent \
    && apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 unixodbc unixodbc-dev gcc g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && ACCEPT_EULA=Y apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
