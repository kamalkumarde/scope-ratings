find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
python main.py
docker-compose down
docker-compose run --rm pipeline
