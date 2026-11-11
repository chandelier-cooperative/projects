#!/bin/bash
set -e

python manage.py wait_for_db
# Wait for migrations
python manage.py wait_for_migrations
# Run the processes
# Without --concurrency Celery starts one process per CPU (~150 MB each). A few users need two,
# and children are recycled so they do not grow. Override with CELERY_CONCURRENCY.
celery -A plane worker -l info \
  --concurrency="${CELERY_CONCURRENCY:-2}" \
  --max-tasks-per-child="${CELERY_MAX_TASKS_PER_CHILD:-200}"