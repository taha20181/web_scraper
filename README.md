## Engineering Approach:

* Architecture: Decoupled extraction and processing using Django, PostgreSQL, and Celery backed by Redis.

* Extraction: Leverages the REST API. Raw JSON payloads are saved in a separate table (acting as a data lake) before processing to ensure data immutability and easy reprocessing without hitting rate limits.

* Processing: Django ORM handles structured storage. JSONField is used for arrays (locations, outcomes) to maintain database flexibility while avoiding over-normalization.

* Change Detection: A custom Python differ runs upon saving a new version, flagging state changes in recruitment, enrollment, and site counts, and logging them to a dedicated TrialChangeSummary table.

* Scalability: Celery workers manage the I/O bound API requests. The pipeline utilizes @shared_task(rate_limit='10/s') to respect the external API constraints and handles exponential backoffs on network failures. Because we use Celery backed by Redis, the workload is distributed.

## Instructions to Run:

Ensure Redis and PostgreSQL are running.

Install requirements: `pip install -r requirements.txt`

Run migrations: `python manage.py migrate`

Start Celery worker: `celery -A your_project worker -l INFO`

Trigger pipeline: `python manage.py run_pipeline`

Start server: `python manage.py runserver`

Navigate to `http://localhost:8000/admin` to view the cleaned, filterable dataset and change logs.
