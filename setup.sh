#!/bin/bash
# setup.sh — Inizializza il progetto FantaNostalgia
# Uso: ./setup.sh

set -e

echo "=== FantaNostalgia Setup ==="
echo ""

read -p "GCP Project ID (es. my-gcp-project): " GCP_PROJECT
read -p "GCS Bucket per il database (es. fantanostalgia-db): " GCS_BUCKET
read -p "Branch di sviluppo (default: main): " DEFAULT_BRANCH
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}

echo ""
echo "Configurazione:"
echo "  GCP Project:  $GCP_PROJECT"
echo "  GCS Bucket:   $GCS_BUCKET"
echo "  Branch:       $DEFAULT_BRANCH"
echo ""
read -p "Confermi? (y/n): " CONFIRM
if [[ "$CONFIRM" != "y" ]]; then
  echo "Annullato."
  exit 0
fi

# Sostituisci placeholder in docs/architecture.md
sed -i "s/your-project-id/$GCP_PROJECT/g" docs/architecture.md
sed -i "s/fantanostalgia-db/$GCS_BUCKET/g" docs/architecture.md

# Crea .env da template
cat > .env << EOF
ENV=development
GCS_BUCKET=$GCS_BUCKET
GCP_PROJECT=$GCP_PROJECT
SECRET_KEY=$(openssl rand -hex 32)
DB_LOCAL_PATH=fantanostalgia.db
EOF

# Crea CLAUDE_MEMORY.md aggiornato
TODAY=$(date +%Y-%m-%d)
sed -i "s/2026-06-10/$TODAY/g" CLAUDE_MEMORY.md
sed -i "s/main/$DEFAULT_BRANCH/g" CLAUDE_MEMORY.md

# Inizializza db locale
sqlite3 fantanostalgia.db < database/schema.sql

echo ""
echo "✓ docs/architecture.md configurato"
echo "✓ .env creato (gitignored)"
echo "✓ CLAUDE_MEMORY.md aggiornato"
echo "✓ Database SQLite locale inizializzato"
echo ""
echo "Prossimi passi:"
echo "  1. Installa dipendenze: pip install -r backend/requirements.txt"
echo "  2. Avvia in locale: docker-compose up"
echo "  3. Avvia Claude Code: claude"
echo ""
echo "Per il deploy:"
echo "  gcloud builds submit --config cloudbuild.yaml"
