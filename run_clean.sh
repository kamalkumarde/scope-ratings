find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

docker-compose down

docker compose run --rm pipeline pytest -v
docker-compose run --rm pipeline
