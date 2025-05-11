## Инструкция по запуску проекта Foodgram
### Предварительные требования

- Установите Docker Compose

### Клонируйте репозиторий
```bash
git clone https://github.com/ZhatkinVyacheslav/foodgram-st.git
cd foodgram-st
```
### Создайте файл с переменными окружения 

Создайте файл .env в той же папке, где находится файл docker-compose.yml и вставьте туда следующие строки

```bash
DB_HOST=db
DB_PORT=5432
POSTGRES_USER=foodgram
POSTGRES_PASSWORD=foodgram
POSTGRES_DB=foodgram
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
```

### Запустите контейнеры

```bash
docker-compose up -d --build
```

### Примените миграции
```bash
docker-compose exec backend python manage.py migrate
```

### Загрузите данные ингредиентов из json
```bash
docker-compose exec backend python manage.py load_json
```

### Соберите все статические файлы
```bash
docker-compose exec backend python manage.py collectstatic
```

### Создайте супрпользователя
После ввода попросит ввести почту, имя и два раза пароль
```bash
docker-compose exec backend python manage.py createsuperuser
```

### ВЫ у цели
После запуска сервис доступен по адресу http://localhost

При надобности остановите котейнер 
```bash
docker-compose down -v --remove-orphans
```