# 📝 Practice FastAPI
## 🚀 Установка и локальный запуск (для заданий до 10)

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/AlmaURepos/practice_fastapi.git
   cd practice_fastapi

2. Создайте виртуальное окружение и активируйте его:

    ```bash
    python -m venv .venv
    .venv/Scripts/activate  # Windows
    source .venv/bin/activate  # macOS/Linux

3. Установите зависимости:

    ```bash
    pip install -r requirements.txt


4. Создайте базы данных PostgreSQL:

    ```bash
    psql -U postgres -c "CREATE DATABASE notes_db; " # local
    psql -U postgres -c "CREATE DATABASE test_notes_db;" # tests
    psql -U postgres -c "CREATE DATABASE practice_notes_db;" #docker

5. Запустите сервер (замените folder_name на имя папки текущего задания):

    ```bash
    uvicorn folder_name.app:app --reload

## Задания с 10 и далее: запуск через Docker

6. Начиная с Задания 10, приложение следует запускать в Docker-контейнерах:

    ```bash
    docker-compose up --build


### Опционально: запуск тестов

7. Вы можете проверить работу приложения с помощью pytest:

    ```bash
    pytest -v folder_name/tests/tests.py





