# telegram_sender.py
import os
import httpx

# --- ВАШИ ДАННЫЕ ---
BOT_TOKEN = "9087441043:AAGXSrpLAgBaUAzDaoagFIHQjOLxXdT5sS4"  # 
CHAT_ID = "7917358762"
# -------------------

def send_pdf_to_telegram(pdf_path: str, req: dict):
    """
    Отправляет PDF-файл в Telegram через официальный API.
    Возвращает (True, "Успех") или (False, "Текст ошибки").
    """
    if "ВАШ" in BOT_TOKEN:
        return False, "Вы не указали BOT_TOKEN в telegram_sender.py"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    # Формируем подпись к файлу (без символов Markdown, чтобы избежать ошибки 400)
    caption = (
        f"📋 Заявка №{req['id']}\n"
        f"📍 Адрес: {req.get('address', '—')}\n"
        f"👤 Клиент: {req.get('fio', '—')}\n"
        f"🔧 Счетчик: {req.get('meter', '—')} (Зав. №: {req.get('meter_serial', '—')})"
    )
    
    try:
        with open(pdf_path, "rb") as f:
            files = {"document": (os.path.basename(pdf_path), f, "application/pdf")}
            data = {
                "chat_id": CHAT_ID,
                "caption": caption
                # Убрали parse_mode, чтобы Telegram не ломался на спецсимволах
            }
            # Отправляем запрос в Telegram
            response = httpx.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            return True, "Успешно отправлено"
    except httpx.HTTPStatusError as e:
        # Если Telegram вернул ошибку, попробуем прочитать её описание
        try:
            error_data = e.response.json()
            error_msg = error_data.get("description", str(e))
        except Exception:
            error_msg = str(e)
        return False, error_msg
    except Exception as e:
        return False, str(e)