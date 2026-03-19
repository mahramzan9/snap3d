web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
worker: cd backend && celery -A app.worker.tasks worker --loglevel=info
