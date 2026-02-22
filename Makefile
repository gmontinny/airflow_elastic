# Airflow Data Lake Project
COMPOSE_FILE = docker-compose-airflow.yml

# Activate environment
activate:
	source .venv/bin/activate

# Airflow services
up:
	docker-compose -f $(COMPOSE_FILE) up -d

down:
	docker-compose -f $(COMPOSE_FILE) down

init:
	docker-compose -f $(COMPOSE_FILE) up airflow-init

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

restart:
	make down && make up

rebuild:
	make down && make up

# Open Airflow UI
browse:
	open http://localhost:8080

unit-tests:
	@echo "Running unit tests..."
