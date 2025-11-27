# Synthetic Data Pipeline (Kafka + Airflow + Postgres + Superset)

Учебный проект демонстрирует микросервисную архитектуру для генерации больших объемов синтетических данных, их потоковой передачи через Kafka, валидации/обработки, сохранения в PostgreSQL и дальнейшей визуализации в Superset. Оркестрация пайплайна выполняется через Apache Airflow.

Основная цель: поднять весь стенд одной командой `docker-compose up --build` и иметь возможность показать полный путь данных от веб‑формы до BI‑дашборда.

---

## Архитектура

### Сервисы и контейнеры

Все сервисы разворачиваются из `docker-compose.yml` в общей сети `analytics-net`:

- **generator** — веб‑сервис на FastAPI для генерации синтетических данных.
  - UI для выбора количества записей и типов полей.
  - Генерирует данные через Faker и отправляет их в producer‑сервис.
- **producer** — HTTP → Kafka продюсер.
  - Принимает JSON с данными от генератора.
  - Публикует сообщения в Kafka‑топик `synthetic_users`.
- **kafka** — брокер сообщений Kafka (Confluent Kafka) + **zookeeper**.
  - Хранит поток синтетических сообщений.
- **kafka-ui** — веб‑интерфейс для мониторинга топиков Kafka.
- **consumer** — сервис обработки и валидации.
  - Читает сообщения из Kafka.
  - Валидирует и нормализует данные.
  - Сохраняет в PostgreSQL (таблица `users_raw`).
- **postgres** — реляционная БД PostgreSQL.
  - Хранит сырые и агрегированные данные.
  - Инициализация схемы через `db/init.sql`.
- **airflow** — оркестратор пайплайна.
  - DAG `synthetic_data_pipeline` управляет генерацией, ожиданием обработки и агрегацией.
- **superset** — BI‑инструмент для визуализации.
  - Подключается к PostgreSQL.
  - Используется для построения дашбордов по `users_raw` и `users_stats`.

Все контейнеры подключены к одной bridge‑сети и обращаются друг к другу по сервисным именам (`kafka`, `postgres`, `generator`, и т.д.).

---

## Поток данных (end‑to‑end)

1. Пользователь открывает веб‑интерфейс генератора (`generator`).
2. Указывает количество записей и набор полей.
3. Generator генерирует записи через Faker и отправляет их HTTP‑запросом на сервис `producer`.
4. Producer отправляет каждую запись отдельным сообщением в Kafka‑топик `synthetic_users`.
5. Consumer подписан на этот топик, валидирует данные и пишет их в таблицу `users_raw` в PostgreSQL.
6. Airflow DAG по запросу:
   - Триггерит генерацию (вызывает `generator`).
   - Ждёт завершения обработки (consumer успевает перелить данные).
   - Запускает SQL‑агрегацию, пересчитывая витрину `users_stats`.
7. Superset подключается к `synthetic_db` и строит дашборды по `users_raw`/`users_stats` (количество записей, распределение по странам, временные ряды).

---

## Технологический стек

- **Язык**: Python 3.11
- **Web / API**: FastAPI + Uvicorn
- **Генерация данных**: Faker
- **Message broker**: Apache Kafka (Confluent images) + Zookeeper
- **Стриминг**: kafka-python
- **Хранилище**: PostgreSQL 16
- **Оркестрация**: Apache Airflow 2.9 (SequentialExecutor, SQLite)
- **BI / визуализация**: Apache Superset 4.0
- **Инфраструктура**: Docker, docker-compose

---

## Структура репозитория

```text
trajectory/
  docker-compose.yml        # Описание всех сервисов и их связей
  README.md                 # Этот файл

  generator/                # Web UI + API генератора синтетических данных (FastAPI)
    Dockerfile
    main.py
    requirements.txt
    templates/
      index.html
      result.html

  producer/                 # HTTP → Kafka producer сервис
    Dockerfile
    main.py
    requirements.txt

  consumer/                 # Kafka consumer: валидация и запись в Postgres
    Dockerfile
    main.py
    requirements.txt

  db/
    init.sql                # Инициализация схемы PostgreSQL (таблица users_raw)

  airflow/
    Dockerfile              # Кастомный образ Airflow (доп. пакеты)
    dags/
      synthetic_pipeline_dag.py   # DAG управления пайплайном
    sql/
      aggregate_users_stats.sql   # SQL-шаблон для агрегации в витрину users_stats

  superset/
    Dockerfile              # Кастомный образ Superset (psycopg2)
```

---

## Сервисы и порты

- **Generator (FastAPI)**: `http://localhost:8080`
- **Kafka UI**: `http://localhost:8085`
- **Airflow Web UI**: `http://localhost:8081`
  - Логин: `admin`
  - Пароль: `admin`
- **Superset Web UI**: `http://localhost:8088`
  - Логин: `admin`
  - Пароль: `admin`
- **Postgres** (для внешних клиентов):
  - host: `localhost`
  - port: `5432`
  - db: `synthetic_db`
  - user: `synthetic_user`
  - password: `synthetic_pass`

Внутри Docker‑сети сервисы обращаются друг к другу по именам контейнеров (`postgres`, `kafka`, `generator`, `producer`, `consumer`, `airflow`, `superset`).

---

## Подключение к базе данных `synthetic_db`

### С хоста (локальный psql / GUI‑клиент)

Параметры подключения:

- **host**: `localhost`
- **port**: `5432`
- **database**: `synthetic_db`
- **user**: `synthetic_user`
- **password**: `synthetic_pass`

Через `psql` (если установлен локально):

```bash
psql "postgresql://synthetic_user:synthetic_pass@localhost:5432/synthetic_db"
```

Через любой GUI‑клиент (DBeaver, DataGrip, TablePlus и т.п.) нужно указать те же параметры.

### Из контейнера postgres

Если `psql` не установлен на хосте, можно подключиться из контейнера:

```bash
docker-compose exec postgres psql -U synthetic_user -d synthetic_db
```

Далее доступны обычные SQL‑запросы, например:

```sql
SELECT COUNT(*) FROM users_raw;
SELECT * FROM users_raw ORDER BY id DESC LIMIT 10;
SELECT * FROM users_stats ORDER BY stat_date DESC, country LIMIT 20;
```

### Подключение из Superset

В Superset (внутри Docker‑сети) используется имя сервиса `postgres`:

- **HOST**: `postgres`
- **PORT**: `5432`
- **DATABASE NAME**: `synthetic_db`
- **USERNAME**: `synthetic_user`
- **PASSWORD**: `synthetic_pass`

Или одной строкой (SQLAlchemy URI):

```text
postgresql+psycopg2://synthetic_user:synthetic_pass@postgres:5432/synthetic_db
```

После успешного подключения в Superset нужно создать datasets для таблиц `users_raw` и `users_stats` и использовать их в графиках/дашбордах.

---

## Подготовка и запуск

### Требования

- Docker
- docker-compose

Рекомендуется запускать из корня репозитория (`trajectory`).

### Первый запуск

```bash
# В корне проекта
docker-compose up --build
```

При первом запуске будут:
- скачаны все образы (`postgres`, `kafka`, `zookeeper`, `kafka-ui`, `apache/airflow`, `apache/superset`),
- собраны кастомные образы (`generator`, `producer`, `consumer`, `airflow`, `superset`),
- инициализирована БД PostgreSQL (таблица `users_raw`),
- инициализированы: Airflow (SQLite), Superset (внутренняя БД).

Для запуска в фоне:

```bash
docker-compose up -d --build
```

Проверить состояние контейнеров:

```bash
docker-compose ps
```

Ожидается, что все ключевые сервисы будут в статусе `Up`.

---

## Подробности по модулям

### 1. Generator (Web UI)

- Фреймворк: FastAPI + Jinja2.
- Основные эндпоинты:
  - `GET /` — HTML‑форма:
    - количество записей (`count`),
    - выбор типов данных (чекбоксы): `name`, `email`, `date`, `password_hash`, `country`, `city`, `phone_number`, `job`, `company`, `ipv4`.
  - `POST /generate` — обрабатывает HTML‑форму:
    - генерирует `count` записей через Faker,
    - отправляет JSON в producer по адресу `http://producer:8001/produce`,
    - показывает HTML‑страницу с результатом (количество, выбранные поля, статус отправки).
  - `POST /api/generate` — чистый API, возвращающий JSON сгенерированных записей без отправки в Kafka.

Генератор не зависит напрямую от Kafka — он общается только с producer‑сервисом по HTTP.

### 2. Producer (ingestion layer)

- Фреймворк: FastAPI.
- Библиотека для Kafka: `kafka-python`.
- Эндпоинт:
  - `POST /produce` — принимает JSON вида:
    ```json
    {
      "records": [ { ... }, { ... } ]
    }
    ```
  - Для каждой записи отправляет сообщение в топик Kafka `synthetic_users`.
  - Обрабатывает ошибки подключения к брокеру (возвращает `503` и логирует ошибки).

Переменные окружения:
- `KAFKA_BROKER` (по умолчанию `kafka:9092`),
- `KAFKA_TOPIC` (по умолчанию `synthetic_users`).

### 3. Kafka + Kafka UI

- **Zookeeper**: `confluentinc/cp-zookeeper:7.4.0`.
- **Kafka**: `confluentinc/cp-kafka:7.4.0`.
  - Параметры:
    - `KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181`
    - `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092`
    - `KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092`
    - `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true` (топики создаются автоматически).

Kafka UI (`provectuslabs/kafka-ui`) подключен к `kafka:9092` и доступен на `http://localhost:8085`.

Используемый топик: **`synthetic_users`**.

### 4. Consumer (Processing & Validation)

- Язык: Python, `kafka-python` + `psycopg2-binary`.
- Логика:
  - Подписывается на топик `synthetic_users`.
  - Десериализует сообщения из JSON.
  - Валидирует и нормализует поля (обрезка длины строк, парсинг дат и т.п.).
  - Вставляет данные в таблицу `users_raw`:
    - `name`, `email`, `event_time`, `password_hash`,
    - `country`, `city`, `phone_number`, `job`, `company`, `ipv4`,
    - `raw_payload` (полный JSON),
    - `error` (ошибка валидации, если была).

Ошибки валидации и вставки логируются, но не ломают весь пайплайн.

### 5. PostgreSQL (Storage)

- Образ: `postgres:16`.
- Переменные окружения:
  - `POSTGRES_DB=synthetic_db`
  - `POSTGRES_USER=synthetic_user`
  - `POSTGRES_PASSWORD=synthetic_pass`
- Volume для данных: `postgres_data:/var/lib/postgresql/data`.
- Init‑скрипт: `./db/init.sql` монтируется в `/docker-entrypoint-initdb.d/init.sql` и создаёт таблицу `users_raw`.

Примеры запросов:

```sql
SELECT COUNT(*) FROM users_raw;
SELECT * FROM users_raw ORDER BY id DESC LIMIT 10;
```

### 6. Airflow (Orchestration)

- Образ: кастомный на основе `apache/airflow:2.9.2`.
  - Установлены дополнительные пакеты: `requests`, `apache-airflow-providers-postgres`.
- Executor: `SequentialExecutor` (совместим с SQLite).
- База Airflow: встроенная SQLite `airflow.db` внутри контейнера.
- DAGs: монтируются из `./airflow/dags`.
- SQL‑шаблоны: монтируются из `./airflow/sql` в `/opt/airflow/sql`.

#### DAG: `synthetic_data_pipeline`

Находится в `airflow/dags/synthetic_pipeline_dag.py`.

Содержит три шага:

1. **`trigger_data_generation` (PythonOperator)**
   - Вызывает `http://generator:8080/generate` с формой:
     - `count=1000`
     - все типы полей включены.

2. **`wait_for_processing` (PythonOperator)**
   - Делает `time.sleep(...)` (по умолчанию 30 секунд), чтобы consumer успел прочитать сообщения и записать их в Postgres.

3. **`aggregate_users_stats` (PostgresOperator)**
   - Исполняет SQL‑шаблон `aggregate_users_stats.sql` (см. ниже).
   - Этот шаблон создаёт витрину `users_stats` и пересчитывает агрегаты по странам и датам.

SQL‑шаблон `aggregate_users_stats.sql`:

```sql
CREATE TABLE IF NOT EXISTS users_stats (
    stat_date DATE,
    country VARCHAR(128),
    total_users BIGINT,
    PRIMARY KEY (stat_date, country)
);

INSERT INTO users_stats (stat_date, country, total_users)
SELECT
    COALESCE(DATE(event_time), CURRENT_DATE) AS stat_date,
    COALESCE(country, 'UNKNOWN') AS country,
    COUNT(*) AS total_users
FROM users_raw
GROUP BY COALESCE(DATE(event_time), CURRENT_DATE), COALESCE(country, 'UNKNOWN')
ON CONFLICT (stat_date, country) DO UPDATE
SET total_users = EXCLUDED.total_users;
```

> Примечание: для использования `PostgresOperator` в DAG нужно создать в Airflow connection к PostgreSQL (см. раздел ниже).

### 7. Superset (BI)

- Образ: кастомный на основе `apache/superset:4.0.2`.
  - Добавлен пакет `psycopg2-binary` для подключения к PostgreSQL.
- При старте контейнера выполняется:
  - `superset db upgrade`
  - `superset fab create-admin` (пользователь `admin/admin`)
  - `superset init`
  - запуск сервера: `superset run -h 0.0.0.0 -p 8088`.

Superset хранит свою внутреннюю БД во volume `superset_home`.

---

## Настройка и использование Airflow

1. Открой Airflow UI: `http://localhost:8081`.
2. Войди под `admin` / `admin`.
3. (Опционально) Создай connection к PostgreSQL для `PostgresOperator`:
   - Меню **Admin → Connections → +**.
   - `Conn Id`: `postgres_analytics`.
   - `Conn Type`: `Postgres`.
   - `Host`: `postgres`.
   - `Schema`: `synthetic_db`.
   - `Login`: `synthetic_user`.
   - `Password`: `synthetic_pass`.
   - `Port`: `5432`.

4. Найди DAG `synthetic_data_pipeline`, включи его (toggle **On**).
5. Запусти DAG (кнопка **Trigger DAG**).
6. В **Graph View** увидишь последовательность задач: `trigger_data_generation → wait_for_processing → aggregate_users_stats`.
7. После успешного прогона все задачи должны быть зелёными.

---

## Настройка и использование Superset

1. Открой Superset: `http://localhost:8088`.
2. Авторизация: `admin` / `admin`.

### Подключение к PostgreSQL

1. **Data → Databases → + Database**.
2. Выбери **PostgreSQL**.
3. Введи URI:
   ```text
   postgresql+psycopg2://synthetic_user:synthetic_pass@postgres:5432/synthetic_db
   ```
4. Сохрани и протестируй соединение.

### Создание datasets

1. **Data → Datasets → + Dataset**.
2. Выбери созданную БД, schema `public`.
3. Добавь таблицы:
   - `users_raw`,
   - `users_stats`.

### Примеры графиков

- **Количество сгенерированных записей** (Big Number / Table):
  - Dataset: `users_raw`.
  - Metric: `COUNT(*)`.

- **Распределение по странам** (Bar / Pie):
  - Dataset: `users_stats`.
  - Dimension: `country`.
  - Metric: `SUM(total_users)`.

- **Временной ряд** (Time-series line/bar):
  - Dataset: `users_stats` или `users_raw`.
  - Time column: `stat_date` (для витрины) или `event_time`/`created_at` (для raw).
  - Metric: `SUM(total_users)` или `COUNT(*)`.

Собери чарты в дашборд (например, `Synthetic Data`), чтобы показать полную картину.

---

## Сценарий демонстрации (Acceptance Criteria)

1. **Deployment**
   - Клонировать репозиторий.
   - Выполнить в корне:
     ```bash
     docker-compose up -d --build
     ```
   - Убедиться, что все контейнеры `Up`:
     ```bash
     docker-compose ps
     ```

2. **Execution (через Airflow)**
   - Открыть Airflow: `http://localhost:8081`.
   - Войти (`admin` / `admin`).
   - (Опционально) создать connection `postgres_analytics` (см. выше).
   - Включить DAG `synthetic_data_pipeline`.
   - Запустить DAG.

3. **Execution (через Web UI генератора)** — альтернативный вариант
   - Открыть `http://localhost:8080`.
   - Задать, например, `count = 1000`, оставить все типы полей, нажать «Сгенерировать».

4. **Process / Monitoring**
   - Открыть Kafka UI: `http://localhost:8085`.
   - Проверить, что есть топик `synthetic_users` и в нём появляются сообщения.
   - В Airflow Graph View наблюдать изменение статусов задач DAG (после запуска через Airflow).

5. **Result: PostgreSQL**
   - Подключиться к PostgreSQL (`synthetic_db`).
   - Выполнить:
     ```sql
     SELECT COUNT(*) FROM users_raw;
     SELECT * FROM users_raw ORDER BY id DESC LIMIT 10;

     SELECT * FROM users_stats ORDER BY stat_date DESC, country LIMIT 20;
     ```
   - Убедиться, что данные появились и агрегаты также посчитаны.

6. **Result: Superset / BI**
   - Открыть Superset: `http://localhost:8088`.
   - Подключить БД `synthetic_db` (один раз).
   - Создать datasets `users_raw` и `users_stats`.
   - Сконструировать дашборд:
     - Метрика общего количества записей.
     - График по странам.
     - Временной ряд.
   - Обновить дашборд и показать рост метрик после каждого запуска DAG или генерации.

---

## Краевые случаи и обработка ошибок

- **Недоступность Kafka**:
  - Producer при ошибке отправки логирует исключение.
  - Отдаёт HTTP‑код `503` при невозможности зафлашить сообщения.

- **Ошибки валидации в consumer**:
  - Слишком длинные строки обрезаются под ограничения полей.
  - Ошибки парсинга дат и другие исключения записываются в поле `error` и не роняют consumer.

- **Инициализация БД**:
  - Init‑скрипт Postgres не содержит внешних зависимостей (dblink и т.п.) и может выполняться на "голом" PostgreSQL.

- **Airflow**:
  - Используется `SequentialExecutor` + SQLite, что упрощает развёртывание в учебной среде.
  - Тяжёлая бизнес‑логика вынесена в отдельные сервисы и SQL‑шаблоны; DAG отвечает только за оркестрацию.

---

## Развитие проекта (идеи)

- Перевести Airflow на Postgres в качестве backend (для прод‑подобной конфигурации).
- Добавить тесты для генератора и consumer.
- Добавить отдельную таблицу для "грязных" записей.
- Добавить поддержку Avro/Schema Registry для сообщений в Kafka.
- Расширить витрины (`users_stats`) дополнительными метриками и разрезами.
