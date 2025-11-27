from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from faker import Faker
import httpx
import os
from typing import List

app = FastAPI(title="Synthetic Data Generator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

fake = Faker()

DATA_TYPES = [
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
]

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://producer:8001/produce")


def generate_record(selected_types: List[str]):
    record = {}
    if "name" in selected_types:
        record["name"] = fake.name()
    if "email" in selected_types:
        record["email"] = fake.email()
    if "date" in selected_types:
        record["date"] = fake.date_time_this_decade().isoformat()
    if "password_hash" in selected_types:
        record["password_hash"] = fake.sha256()
    if "country" in selected_types:
        record["country"] = fake.country()
    if "city" in selected_types:
        record["city"] = fake.city()
    if "phone_number" in selected_types:
        record["phone_number"] = fake.phone_number()
    if "job" in selected_types:
        record["job"] = fake.job()
    if "company" in selected_types:
        record["company"] = fake.company()
    if "ipv4" in selected_types:
        record["ipv4"] = fake.ipv4()
    return record


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data_types": DATA_TYPES},
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    count: int = Form(...),
    data_types: List[str] = Form(...),
):
    records = [generate_record(data_types) for _ in range(count)]

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            await client.post(PRODUCER_URL, json={"records": records})
            status = "Отправлено в Kafka через producer-сервис"
        except Exception as e:
            status = f"Ошибка при отправке в producer: {e}"

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "count": count,
            "data_types": data_types,
            "status": status,
        },
    )


@app.post("/api/generate", response_class=JSONResponse)
async def api_generate(count: int, data_types: List[str]):
    records = [generate_record(data_types) for _ in range(count)]
    return {"records": records}
