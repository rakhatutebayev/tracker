# Полная система GPS трекинга для Казахстана

## 🎯 Возможности

✅ **Реал-тайм отслеживание** машин на интерактивной карте (Live WebSocket)
✅ **Детальные отчеты по маршрутам** (поездки с датой/временем выезда-приезда)
✅ **Итоговые статистики** (расстояние, время в пути, скорость)
✅ **Экспорт в CSV** для анализа в Excel
✅ **Поддержка русского языка** полностью
✅ **Оптимизирован для Казахстана** (2GIS карты)
✅ **Масштабируемая архитектура** (Docker Compose)

## 📦 Структура проекта

```
tracker/
├── backend/              # Python FastAPI
│   ├── app/
│   │   ├── core/         # Config, DB, settings
│   │   ├── models/       # SQLAlchemy + Pydantic schemas
│   │   ├── api/          # REST endpoints + WebSocket
│   │   ├── services/     # Trip detection logic
│   │   └── main.py       # FastAPI app
│   ├── requirements.txt
│   ├── .env
│   └── Dockerfile
│
├── frontend/             # React + Vite
│   ├── src/
│   │   ├── components/   # LiveMap, TripsReport, SummaryReport
│   │   ├── pages/        # MainLayout
│   │   ├── services/     # API client
│   │   ├── hooks/        # useWebSocket
│   │   ├── store/        # Zustand state
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
│
├── traccar/              # Оригинальная Traccar (для миграции)
└── docker-compose.yml    # Вся система в контейнерах
```

## 🚀 Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

```bash
cd /Users/rakhat/Documents/webhosting/tracker

# Запустить всю систему
docker-compose up -d

# Инициализировать БД (первый раз)
docker-compose exec backend python -m app.core.database
```

Откроется:
- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8001/docs
- **Database**: localhost:5432

### Вариант 2: Локально (разработка)

#### Backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# Создать .env с подключением к БД
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://traccar:traccar@localhost:5432/traccar
DATABASE_ECHO=False
DEBUG=True
EOF

# Запустить
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Откроется http://localhost:3000

## 📊 API Endpoints

### Устройства

```bash
GET /api/devices                    # Список машин
GET /api/devices/{id}               # Одна машина
```

### Позиции

```bash
GET /api/positions/latest           # Последние позиции (для карты)
GET /api/positions/{device_id}      # История позиций машины
```

### Отчеты

```bash
POST /api/reports/trips             # Поездки за период
GET /api/reports/summary            # Итоги (расстояние, время, скорость)
```

### WebSocket (Live)

```
ws://localhost:8001/ws/tracker?devices=1,2,3
```

Подписка на live обновления позиций.

## 🗺️ Карта и 2GIS

По умолчанию — **OpenStreetMap**. Можно включить **2GIS** тайлы через переменные окружения на этапе сборки фронтенда:

- `VITE_MAP_PROVIDER=2gis`
- `VITE_2GIS_KEY=ваш_ключ`

В docker-compose это уже предусмотрено (раскомментируйте и задайте ключ в секции build.args → frontend).

## 🔧 Конфигурация

### Backend (.env)

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
TRIP_MIN_SPEED_KMH=5.0              # Скорость для счета в поездку
TRIP_IDLE_THRESHOLD_SEC=300         # Время остановки (сек)
TRIP_MIN_DURATION_SEC=60            # Минимум длина поездки (сек)
DEBUG=False
```

### Frontend (переменные Vite)

Базовые адреса API/WS пробрасываются при сборке и уже настроены в docker-compose:

- `VITE_API_BASE` — по умолчанию `http://localhost:8001/api`
- `VITE_WS_BASE` — по умолчанию `ws://localhost:8001`
- `VITE_MAP_PROVIDER` — `osm` (по умолчанию) или `2gis`
- `VITE_2GIS_KEY` — ключ 2GIS, если выбрали 2gis

## 📈 Примеры использования

### Получить отчет по машине за месяц

```bash
curl -X POST http://localhost:8001/api/reports/trips \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "from_date": "2025-11-01T00:00:00Z",
    "to_date": "2025-11-30T23:59:59Z"
  }'
```

### WebSocket subscribe

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/tracker?devices=1,2,3');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log(msg.type, msg.data);  // position_update, trip_start, trip_end
};
```

## 🔄 Миграция из Traccar

Существующие данные из старой Traccar БД можно перенести:

```sql
-- Export устройств и позиций
psql -h localhost -U traccar -d traccar \
  -c "COPY (SELECT * FROM tc_devices) TO STDOUT" > devices.csv

psql -h localhost -U traccar -d traccar \
  -c "COPY (SELECT * FROM tc_positions) TO STDOUT" > positions.csv

# Затем импортировать в новую БД
# (скрипт миграции готовится)
```

## 🧪 Тестирование

### Backend

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run test
```

## 📝 Логирование и мониторинг

### Backend logs

```bash
docker-compose logs -f backend
```

### Frontend logs

```bash
docker-compose logs -f frontend
```

### Database

```bash
docker-compose exec postgres psql -U traccar -d traccar -c "SELECT count(*) FROM positions;"
```

## 🚨 Troubleshooting

### 1. WebSocket не подключается

Проверить:
```bash
# Backend слушает на 8000
curl http://localhost:8000/health

# Frontend может достучаться
curl http://localhost:3000
```

### 2. БД не инициализируется

```bash
docker-compose down -v  # Удалить volume
docker-compose up -d
docker-compose exec backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 3. Позиции не отображаются на карте

- Проверить `/api/devices` и `/api/positions/latest` в http://localhost:8000/docs
- Убедиться, что БД содержит данные

## 📚 Документация

- **Backend**: `/backend/README.md`
- **Frontend**: `/frontend/README.md`
- **Trip Detection**: `/backend/app/services/trip_service.py`

## 🎓 Принципы

### Trip Detection (Детектирование поездок)

1. **Движение**: speed >= 5 км/ч
2. **Остановка**: speed < 5 км/ч на 300+ сек
3. **Вычисления**: Haversine distance, средняя/макс скорость
4. **Фильтр**: Только поездки >= 60 сек сохраняются

### Live Tracking (WebSocket)

1. Клиент подписывается на device IDs
2. Сервер отправляет обновления по мере поступления новых позиций
3. Карта обновляется в реальном времени
4. При обрыве соединения — автопереподключение через 3 сек

### Отчеты (REST API)

1. Получить поездки за период
2. Вычислить статистику (расстояние, время, скорость)
3. Возвращить структурированный JSON
4. Экспортировать в CSV (клиент)

## 🔐 Безопасность (TODO)

- [ ] JWT authentication
- [ ] RBAC (Role-Based Access Control)
- [ ] Rate limiting
- [ ] HTTPS/WSS
- [ ] API keys для external integrations

## 🌍 Локализация

Интерфейс полностью на **русском**:
- Ant Design локаль
- Dayjsru
- Все сообщения, даты, валюты

## 📞 Support

Любые вопросы по архитектуре, расширению функционала, интеграции с 2GIS API — готов помочь! 🚀
