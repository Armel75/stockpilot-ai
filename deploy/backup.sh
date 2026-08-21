#!/usr/bin/env bash
# ============================================================
# StockPilot AI — Sauvegarde manuelle de la base (PostgreSQL)
# Usage : ./backup.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups/db

DB_USER="${POSTGRES_USER:-stockpilot}"
DB_NAME="${POSTGRES_DB:-stockpilot}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="backups/db/stockpilot_${TS}.dump"

echo "▶ Sauvegarde de ${DB_NAME} → ${OUT}"
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc -f "/backups/stockpilot_${TS}.dump"

echo "▶ Nettoyage des sauvegardes de plus de 7 jours…"
find backups/db -name "*.dump" -mtime +7 -delete

echo "✓ Sauvegarde terminée : ${OUT}"
