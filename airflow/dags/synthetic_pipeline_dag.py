from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
import requests


def trigger_generator(**context):
    count = context["params"].get("count", 1000)
    data = {
        "count": str(count),
        "data_types": [
            "name",
            "email",
            "date",
            "password_hash",
            "country",
            "city",
            "phone_number",
            "job",
            "company",
            "ipv4",
        ],
    }
    resp = requests.post("http://generator:8080/generate", data=data, timeout=60)
    resp.raise_for_status()


def wait_for_processing(**context):
    # Упрощённо: просто ждём, пока consumer обработает сообщения
    import time

    wait_seconds = context["params"].get("wait_seconds", 30)
    time.sleep(wait_seconds)


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
}


with DAG(
    dag_id="synthetic_data_pipeline",
    default_args=default_args,
    description="Учебный DAG: генерация -> Kafka -> Postgres",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    template_searchpath=["/opt/airflow/sql"],
    tags=["synthetic", "kafka", "postgres"],
) as dag:

    generate_task = PythonOperator(
        task_id="trigger_data_generation",
        python_callable=trigger_generator,
        provide_context=True,
        params={"count": 1000},
    )

    wait_task = PythonOperator(
        task_id="wait_for_processing",
        python_callable=wait_for_processing,
        provide_context=True,
        params={"wait_seconds": 30},
    )

    aggregate_task = PostgresOperator(
        task_id="aggregate_users_stats",
        postgres_conn_id="postgres_analytics",
        sql="aggregate_users_stats.sql",
    )

    generate_task >> wait_task >> aggregate_task
