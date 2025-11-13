#!/bin/bash
set -e

echo "Atualizando repositório..."
git pull origin main  # ou sua branch principal

echo "Fazendo deploy no Scrapyd..."
docker-compose exec scrapyd scrapyd-deploy

echo "Deploy concluído!"