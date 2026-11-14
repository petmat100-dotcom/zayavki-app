# pdf_export.py
import os
from datetime import datetime
from fpdf import FPDF

class RequestPDF(FPDF):
    def header(self):
        self.set_font('DejaVu', 'B', 16)
        self.set_text_color(13, 71, 161)
        self.cell(0, 10, 'Заявка на ремонт', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Страница {self.page_no()}', 0, 0, 'C')

def generate_request_pdf(req: dict, out_dir: str | None = None) -> str:
    if out_dir is None:
        out_dir = os.path.join(os.getenv("FLET_APP_STORAGE_DATA", "."), "exports")
    os.makedirs(out_dir, exist_ok=True)
    file_path = os.path.join(out_dir, f"Заявка_{req['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    pdf = RequestPDF()
    pdf.add_page()
    
    # Подключаем шрифт с поддержкой кириллицы
    font_dir = os.path.join(os.path.dirname(__file__), "assets")
    pdf.add_font("DejaVu", "", os.path.join(font_dir, "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", os.path.join(font_dir, "DejaVuSans-Bold.ttf"))
    pdf.set_font("DejaVu", size=10)

    def add_section(title, rows):
        pdf.set_font("DejaVu", "B", 12)
        pdf.set_text_color(13, 71, 161)
        pdf.cell(0, 8, title, 0, 1)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(0)
        for k, v in rows:
            if v:
                pdf.multi_cell(0, 6, f"{k}: {v}", 0, 1)
        pdf.ln(3)

    add_section("Данные объекта", [
        ("Объект", req.get("obj_name")), ("Адрес", req.get("address")),
        ("Клиент", req.get("fio")), ("Создал заявку", req.get("created_by"))
    ])
    add_section("Данные счётчика", [
        ("Тип", req.get("meter")), ("Заводской №", req.get("meter_serial")),
        ("Показания", req.get("meter_readings")), ("Номер пломбы", req.get("meter_seal")),
        ("Неисправность", req.get("malfunction"))
    ])
    if req.get("status") == "completed":
        add_section("Выполнение ремонта", [
            ("Исполнитель", req.get("repaired_by")), ("Процесс ремонта", req.get("repair_process")),
            ("Заменённые детали", req.get("repair_parts")), ("Стоимость", f"{req.get('repair_cost')} ₽")
        ])

    # Добавление фотографий
    photos = req.get("photos") or {}
    photo_titles = {"meter": "Счётчик", "serial": "Зав. номер", "general": "Общее", "object": "Объект", "seal": "Пломба"}
    has_photos = False

    for key, title in photo_titles.items():
        path = photos.get(key)
        if path and os.path.exists(path):
            if not has_photos:
                pdf.add_page()
                pdf.set_font("DejaVu", "B", 12)
                pdf.set_text_color(13, 71, 161)
                pdf.cell(0, 10, "Фотофиксация", 0, 1)
                has_photos = True
            try:
                pdf.set_font("DejaVu", "B", 9)
                pdf.set_text_color(0)
                pdf.cell(0, 6, title, 0, 1)
                pdf.image(path, w=80)
                pdf.ln(3)
            except Exception:
                pass

    pdf.output(file_path)
    return file_path
