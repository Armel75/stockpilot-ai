# StockPilot AI — Sales & Inventory Intelligence Agent

Agent IA de **pilotage intelligent des stocks et de la demande** : il croise les données
de **ventes** et de **stock** (issues de SAGE X3) pour produire automatiquement des
**affirmations priorisées** — tendances, prévisions, risques, opportunités — sans que
personne n'ait à poser de question.

> Ce n'est pas un chatbot : c'est un agent qui **parle tout seul**, chaque matin.

---

## La boucle de l'agent

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. PERCEVOIR   Ingestion SAGE X3 (vues SQL Server) ou jeu de démo    │
│ 2. ANALYSER    Prévision 30 j (Holt-Winters) + signaux (règles)      │
│ 3. DÉCIDER     DeepSeek priorise & rédige les affirmations (LLM)     │
│ 4. AGIR        Page « Pilotage » + point de situation du jour        │
│ 5. APPRENDRE   Feedback exact/faux + score prévision vs réalité      │
└──────────────────────────────────────────────────────────────────────┘
```

**Règle d'or** : le LLM ne calcule jamais. Tous les chiffres viennent du moteur
déterministe (statsmodels + règles métier). DeepSeek ne fait que **prioriser,
expliquer et rédiger** à partir des faits calculés. En cas d'indisponibilité du LLM,
l'agent bascule automatiquement sur une narration déterministe.

---

## Détection des signaux (règles métier)

| Signal | Règle | Priorité |
|---|---|---|
| Rupture imminente | Couverture < 15 j (7 j → P0) | P0 / P1 |
| Surstock | Couverture > 90 j | P1 / P2 |
| Stock dormant | Aucune vente depuis 60 j, stock > 0 | P2 |
| Accélération | Ventes 30 j > +40 % vs période précédente | P1 |
| Opportunité | Marge ≥ 25 % + excédent / forte demande | P1 / P2 |
| Réappro | Prévision sur délai + stock sécurité − stock − transit > 0 | P1 / P2 |

---

## Stack

| Couche | Techno |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 · APScheduler |
| Worker asynchrone | Redis 7 + RQ (l'exécution de l'agent ne bloque plus l'API) |
| Prévision | statsmodels (Holt-Winters ETS) — repli moyenne mobile |
| LLM narrateur | DeepSeek (API compatible OpenAI, clé dans `.env`) |
| Stockage | PostgreSQL 16 (Docker) — ou SQLite en dev |
| Ingestion | pyodbc + ODBC Driver 18 → vues SAGE X3 (SQL Server) |
| Frontend | React 18 · TypeScript · Vite · Tailwind · Recharts |
| Observabilité | Prometheus + Grafana + Loki + Promtail |
| DevOps | Docker Compose (dev/prod) · Caddy HTTPS · GitHub Actions CI · backups auto |

---

## Démarrage rapide

### Option A — Docker (dev complet avec worker asynchrone)

```bash
docker compose up --build -d
# Frontend : http://localhost:5173   Backend : http://localhost:8000/docs   Redis : localhost:6379
```

> L'agent s'exécute dans le **worker** (Redis/RQ) : « Générer le point » répond instantanément
> et le calcul (prévisions + DeepSeek) tourne en arrière-plan. Sans Redis, l'API bascule
> automatiquement en mode synchrone (repli).

### Option B — Local (dev)

**Backend**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# PostgreSQL via Docker (ou basculez sur SQLite dans .env)
docker compose up -d db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173 (proxy /api → backend:8000)
```

---

## Connexion aux données SAGE X3

Les paramètres de connexion (vues SQL Server) sont dans **`.env`** (fichier gitignoré) :

```
X3_SALES_SERVER, X3_SALES_USER, X3_SALES_PASSWORD, X3_SALES_VIEW   # vue des ventes
X3_STOCK_SERVER, X3_STOCK_USER, X3_STOCK_PASSWORD, X3_STOCK_VIEW   # vue des stocks
```

> ⚠️ **ADAPTEZ ICI** : dans `backend/app/ingestion/sagex3.py`, le dictionnaire
> `SALES_COLS` / `STOCK_COLS` mappe les noms de colonnes attendus vers ceux de **vos**
> vues X3. Ajustez ces noms à votre schéma réel.

**Modes d'ingestion** (`INGESTION_MODE` dans `.env`) :
- `auto` (défaut) : essaie SAGE X3, bascule sur le jeu de démo si injoignable ;
- `sagex3` : SAGE X3 uniquement ;
- `seed` : jeu de démonstration (8 mois de ventes réalistes, anomalies incluses).

Au premier démarrage, si la base est vide, le jeu de démonstration est chargé
automatiquement : l'agent est **immédiatement fonctionnel**.

---

## Sécurité (recommandations)

- Les identifiants (`sa`) fournis sont stockés **uniquement** dans `.env` (gitignoré).
- ⚠️ **En production** : créez un compte SQL Server **lecture seule** dédié à l'app
  (jamais `sa`), et un utilisateur PostgreSQL dédié.
- Ne committez jamais `.env`.

---

## API principale

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/pilotage` | Point de situation : KPIs + affirmations + fraîcheur |
| POST | `/api/v1/system/agent/run` | Exécute la boucle complète de l'agent |
| GET | `/api/v1/signals` | Signaux ouverts |
| GET | `/api/v1/forecasts` | Séries de prévision 30 j |
| GET | `/api/v1/products` | Catalogue + stocks + signaux |
| POST | `/api/v1/assertions/{id}/feedback` | Exact / Faux (boucle d'apprentissage) |
| GET | `/api/v1/accuracy/latest` | Score de précision (MAPE, biais) |
| GET | `/api/v1/system/health` | Santé du système |

---

## DevOps & Déploiement

### Environnements

| Fichier | Rôle |
|---|---|
| `docker-compose.yml` | Dev : db + redis + backend + worker + frontend |
| `docker-compose.prod.yml` | Prod : + Caddy (HTTPS) + backup automatique PostgreSQL |
| `docker-compose.observability.yml` | Supervision : Prometheus, Grafana, Loki, Promtail |
| `.github/workflows/ci.yml` | CI : lint (ruff) + tests (pytest) + build frontend + images Docker |

### Déploiement en production (1 commande)

```bash
cp .env.prod.example .env   # puis remplir les secrets
./deploy/deploy.sh           # build + up -d + vérification de santé
```

- **HTTPS automatique** : Caddy + Let's Encrypt (`deploy/Caddyfile` — remplacez le domaine).
- **Backups** : sauvegarde quotidienne PostgreSQL (7 j de rétention) + `./deploy/backup.sh` manuel.
- **Secrets** : uniquement dans `.env` (gitignoré) — jamais committés.

### Observabilité

```bash
docker compose -f docker-compose.observability.yml up -d
# Grafana : http://localhost:3000 (admin / GRAFANA_PASSWORD, dashboard pré-provisionné)
# Prometheus : http://localhost:9090
```

Métriques exposées par le backend sur `/metrics` : requêtes HTTP, exécutions de l'agent par statut,
durée de la dernière exécution, signaux ouverts.

---

## Feuille de route

- [x] **Phase 1** — prévision, signaux, narration, Pilotage, feedback, précision
- [ ] **Phase 2** — notifications ciblées, multi-agences (transferts proposés)
- [ ] **Phase 3** — drafts de commandes fournisseur (validation humaine)
