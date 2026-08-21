#!/usr/bin/env bash
# ============================================================
# StockPilot AI — Déploiement en production (1 commande)
# Prérequis : Docker + Docker Compose installés sur le serveur.
# Usage : ./deploy.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "▶ Vérification de la configuration…"
[ -f .env ] || { echo "✗ .env introuvable. Copiez .env.prod.example vers .env et remplissez."; exit 1; }

echo "▶ Build des images…"
docker compose -f docker-compose.prod.yml build

echo "▶ Démarrage de la stack…"
docker compose -f docker-compose.prod.yml up -d

echo "▶ Vérification de la santé…"
sleep 8
curl -sf http://localhost:8000/api/v1/system/health >/dev/null \
  && echo "✓ Backend sain" \
  || echo "⚠ Backend pas encore prêt — vérifiez les logs : docker compose -f docker-compose.prod.yml logs -f"

echo "✓ Déploiement terminé."
echo "  Logs   : docker compose -f docker-compose.prod.yml logs -f"
echo "  Backup : docker compose -f docker-compose.prod.yml logs -f backup"
