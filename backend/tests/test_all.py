import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud, schemas
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_root():
    response = client.get("/")
    assert response.status_code == 404
    assert "message" in response.json()


def test_create_task():
    response = client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "Test Description",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["completed"] is False
    assert "id" in data


def test_get_tasks():
    client.post("/tasks/", json={"title": "Task 1"})
    client.post("/tasks/", json={"title": "Task 2"})
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2


def test_get_task_by_id():
    create_response = client.post("/tasks/", json={"title": "Get Test"})
    task_id = create_response.json()["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test"


def test_get_task_not_found():
    response = client.get("/tasks/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Задача не найдена"


def test_update_task():
    create_response = client.post("/tasks/", json={"title": "Update Test"})
    task_id = create_response.json()["id"]
    response = client.put(f"/tasks/{task_id}", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["completed"] is True


def test_delete_task():
    create_response = client.post("/tasks/", json={"title": "Delete Test"})
    task_id = create_response.json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


def test_create_task_invalid_priority():
    response = client.post(
        "/tasks/",
        json={"title": "Test", "priority": "invalid"}
    )
    assert response.status_code == 422


def test_create_task_empty_title():
    response = client.post("/tasks/", json={"title": ""})
    assert response.status_code == 422
    