# Python Backend: Live Tracking & Reports

## Структура

```
app/
├── core/
│   ├── config.py        # Settings (DB, server, trip detection)
│   └── database.py      # Async SQLAlchemy engine & sessions
├── models/
│   ├── database.py      # SQLAlchemy ORM: Device, Position, Trip, Stop, Event, Geofence
│   └── schemas.py       # Pydantic schemas for API
├── api/
│   ├── routes.py        # REST endpoints (/api/devices, /api/positions, /api/reports/*)
│   └── websocket.py     # WebSocket manager for live updates
├── services/
│   └── trip_service.py  # Trip detection & aggregation
└── main.py              # FastAPI app + startup/shutdown
```

## Функциональность

### 1. Live Map (Реальное время)

**WebSocket endpoint**: `ws://localhost:8000/ws/tracker?devices=1,2,3`

Клиент подписывается на обновления позиций машин:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tracker?devices=1,2,3');
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'position_update') {
        updateMap(msg.data);  // {device_id, device_name, latitude, longitude, speed, fix_time}
    }
};
```

**REST для последних позиций**: `GET /api/positions/latest`

### 2. Отчеты по маршрутам (Trips)

**POST /api/reports/trips**

Входные параметры:
- `device_id`: ID машины (опционально, для всех если не указано)
- `from_date`: Начало периода
- `to_date`: Конец периода

Результат содержит:
- **device_name**: Название машины
- **start_point**: Координаты пункта выезда
- **start_time**: Дата и время выезда
- **end_point**: Координаты пункта приезда
- **end_time**: Дата и время приезда
- **duration_hours**: Время в пути (часы)
- **distance_km**: Расстояние (км)
- **avg_speed** / **max_speed**: Средняя и максимальная скорость

**GET /api/reports/summary** — итоговый отчет по месяцу/неделе

### 3. Алгоритм детектирования поездок

1. Получаем позиции → группируем по скорости.
2. Speed >= 5 км/ч → движение (поездка).
3. Speed < 5 км/ч на 300+ сек → остановка.
4. Вычисляем расстояние (Haversine), время, скорость.
5. Сохраняем только поездки >= 60 сек.

## Запуск

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API Docs**: http://localhost:8000/docs

