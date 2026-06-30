# Сжатие фото профиля

## Цель
Уменьшить трафик и нагрузку при загрузке фото анкет, сжимая изображения до HD на фронтенде.

## Решение

### 1. Frontend helper
- Файл: `docs/js/utils/image.js`
- Функция: `compressImage(file, { maxDimension = 1280, quality = 0.85 })`
- Логика:
  - Загружает файл в `Image`.
  - Масштабирует с сохранением пропорций так, чтобы большая сторона была ≤ 1280 px.
  - Рисует на `<canvas>` и экспортирует в `Blob` типа `image/jpeg` с качеством 0.85.
  - При ошибке возвращает исходный файл.

### 2. Интеграция
- `docs/js/api.js`: `uploadPhoto(file)` сжимает файл через `compressImage` перед добавлением в `FormData`.
- Остальные места (`registration.js`, `profileEditor.js`, `editField.js`) не меняются.

### 3. Backend guard
- `web_routes.py`: уменьшить `MAX_PHOTO_SIZE` с 5 МБ до 3 МБ как финальную защиту.

### 4. Тесты
- Добавить тест `test_upload_photo_rejects_oversized` для проверки лимита 3 МБ.
