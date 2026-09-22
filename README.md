# Hop & Barley — інтернет-магазин (Django / DRF)

[![CI](https://github.com/kfr-fdv/m3-final/actions/workflows/ci.yml/badge.svg)](https://github.com/kfr-fdv/m3-final/actions/workflows/ci.yml)

Навчальний інтернет-магазин товарів для домашнього пивоваріння: веб-вітрина на Django-шаблонах
із session-автентифікацією та REST API з JWT для зовнішніх клієнтів. Інфраструктура — PostgreSQL
у Docker, менеджер залежностей — `uv`.

## Можливості

- **Каталог і пошук:** список товарів із пагінацією, фільтри за категорією (з підкатегоріями)
  та ціною, пошук за назвою/описом, сортування за ціною, новизною, рейтингом, популярністю.
- **Сторінка товару:** опис, рейтинг, відгуки; відгук можна залишити лише після покупки.
- **Кошик:** зберігається в сесії, перевірка залишків на складі.
- **Оформлення замовлення:** транзакція, списання складу, email покупцю та адміністратору.
- **Особистий кабінет:** реєстрація, вхід/вихід, профіль, зміна пароля, історія та скасування замовлень.
- **Адмінка:** керування товарами/замовленнями/відгуками, дії над замовленнями, сторінка аналітики.
- **REST API:** товари, кошик, замовлення, відгуки, реєстрація та JWT-автентифікація, Swagger-документація.

## Стек

Django 6 · Django REST Framework · SimpleJWT · drf-spectacular · django-filter · PostgreSQL 17 ·
Docker Compose · uv · pytest · ruff · mypy.

## Швидкий старт (Docker)

```bash
git clone https://github.com/kfr-fdv/m3-final.git
cd m3-final
cp .env.example .env.dev
```

У `.env.dev` вкажіть (для запуску в Docker):

```env
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DATABASE_URL=postgresql://postgres:postgres@db:5432/final3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=final3
SHOP_NAME="Hop & Barley"
```

Запуск:

```bash
docker compose up --build        # міграції застосуються автоматично; сайт на http://localhost:8000/
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo   # демо-дані (категорії, товари, відгуки, замовлення)
```

- Вітрина: <http://localhost:8000/>
- Адмінка: <http://localhost:8000/admin/> · Аналітика: <http://localhost:8000/admin/analytics/>
- Swagger: <http://localhost:8000/api/docs/>

## REST API

Базовий префікс — `/api/`. Автентифікація зовнішніх клієнтів — JWT (access + refresh).

```bash
# Реєстрація
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"john","email":"john@example.com","password":"StrongPass123!"}'

# Отримати JWT
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"StrongPass123!"}'
# -> {"access":"<ACCESS>","refresh":"<REFRESH>"}

# Список товарів (пагінація, пошук, сортування)
curl "http://localhost:8000/api/products/?search=citra&ordering=-rating_avg"

# Створити замовлення (потрібен токен)
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer <ACCESS>" -H "Content-Type: application/json" \
  -d '{"full_name":"John","email":"john@example.com","phone":"123","shipping_address":"Kyiv","payment_method":"card","items":[{"product":1,"quantity":2}]}'

# Оновити access-токен
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh":"<REFRESH>"}'
```

Основні ресурси: `products/`, `products/<id>/reviews/`, `cart/`, `orders/`, `users/register/`,
`users/login/`, `token/refresh/`. Права доступу: користувач бачить і змінює лише свої замовлення.

## Тести та якість коду

Локально (потрібен `uv`) або в контейнері (`docker compose exec web ...`):

```bash
uv run pytest --cov=apps --cov-report=term-missing   # тести з покриттям
uv run ruff check .                                  # лінтер
uv run ruff format --check .                         # форматування
uv run mypy .                                        # перевірка типів
```

CI (GitHub Actions, `.github/workflows/ci.yml`) на push/PR у `main` піднімає PostgreSQL і
запускає ruff, ruff format, mypy та pytest.

## Структура проєкту

```
config/            # налаштування (base/local/dev/prod), urls, wsgi/asgi
apps/
  core/            # health, аналітика, context processors, команда seed_demo
  catalog/         # категорії, товари, фільтри, каталог і сторінка товару
  orders/          # кошик (сесія), оформлення, замовлення, email, сервіси
  accounts/        # кастомний User, реєстрація/вхід/профіль
  reviews/         # відгуки (гейт «після покупки»)
  api/             # DRF: серіалізатори, в'юсети, JWT, Swagger
templates/         # Django-шаблони (на основі дизайну Hop-and-Barley)
static/            # CSS/JS/зображення
tests/             # загальні тести
```

## Чек-лист реалізації

- [x] Запуск через `docker compose up`, PostgreSQL
- [x] Каталог: фільтри, пошук, пагінація
- [x] Сторінка товару: деталі, відгуки, додавання в кошик
- [x] Кошик: керування вмістом, сума, перевірка залишків
- [x] Оформлення замовлення: створення, email, валідація
- [x] Особистий кабінет: реєстрація, вхід, історія, редагування профілю
- [x] REST API: JWT, документація, права доступу
- [x] Адмін-панель: аналітика, фільтри, зручне керування
- [x] Swagger/OpenAPI документація
- [x] Типізація та докстрінги, лінтери (ruff/mypy) без помилок
- [x] Тести (покриття ≥ 80%)
- [x] README та CI
