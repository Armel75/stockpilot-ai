-- ============================================================
-- StockPilot AI — initialisation PostgreSQL
-- NB : le schéma applicatif est créé automatiquement par
-- SQLAlchemy (Base.metadata.create_all) au démarrage du backend.
-- Ce script est exécuté par Docker uniquement à la première
-- création du volume (docker-entrypoint-initdb.d).
-- ============================================================

-- Rien à créer ici : les tables (products, sales, stock_snapshots,
-- forecasts, signals, assertions, daily_reports, accuracy_scores,
-- ingestion_logs) sont gérées par l'application.
SELECT 'StockPilot AI — schéma géré par SQLAlchemy au démarrage';
