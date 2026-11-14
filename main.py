import flet as ft
import os
import shutil
import tempfile
from datetime import datetime

import database as db
from pdf_export import generate_request_pdf
from telegram_sender import send_pdf_to_telegram

try:
    import flet_camera as fc
except ImportError:
    fc = None


def main(page: ft.Page):
    page.title = "Система заявок и ремонтов"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    # Инициализация БД
    db.init_db()

    search_query_active = ""
    search_query_completed = ""

    list_active = ft.ListView(expand=True, spacing=10, padding=10)
    list_completed = ft.ListView(expand=True, spacing=10, padding=10)

    # --- ОБРАБОТЧИК ФОТО ---
    file_picker = ft.FilePicker()
    current_photo_key = None
    new_photo_paths = {"meter": None, "serial": None, "general": None, "object": None, "seal": None}
    form_photo_widgets = {}

    def persist_photo(source_path, key):
        if not source_path or not os.path.exists(source_path):
            return None
        data_dir = os.getenv("FLET_APP_STORAGE_DATA", ".")
        photos_dir = os.path.join(data_dir, "photos")
        os.makedirs(photos_dir, exist_ok=True)
        ext = os.path.splitext(source_path)[1] or ".jpg"
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{key}{ext}"
        dest = os.path.join(photos_dir, filename)
        shutil.copy2(source_path, dest)
        return dest

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            new_photo_paths[current_photo_key] = e.files[0].path
            update_form_photo_ui(current_photo_key, e.files[0].path)

    file_picker.on_result = on_file_picked

    def update_form_photo_ui(key, path):
        form_photo_widgets[key]["img"].src = path
        form_photo_widgets[key]["img"].visible = True
        form_photo_widgets[key]["status"].value = "✅ Фото добавлено"
        form_photo_widgets[key]["status"].color = ft.Colors.GREEN
        page.update()

    def pick_gallery(e, key):
        nonlocal current_photo_key
        current_photo_key = key
        file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)

    def open_camera(e, key):
        if str(page.platform) == "windows" or fc is None:
            page.show_dialog(ft.SnackBar(ft.Text("Камера не работает на ПК.", bgcolor=ft.Colors.RED)))
            return

        cam = fc.Camera(preview_enabled=True, expand=True)

        def take_picture(ev):
            async def capture():
                img_bytes = await cam.take_photo()
                temp_file = os.path.join(tempfile.gettempdir(), f"{key}_photo.jpg")
                with open(temp_file, "wb") as f:
                    f.write(img_bytes)
                new_photo_paths[key] = temp_file
                update_form_photo_ui(key, temp_file)
                close_camera(None)
            page.run_task(capture)

        camera_view = ft.Container(
            content=ft.Column([
                ft.Text("Сделайте фото", size=20, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                cam,
                ft.Row([
                    ft.Button("Отмена", on_click=lambda _: close_camera(None)),
                    ft.Button("📸 Снять", on_click=take_picture, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)
            ]), bgcolor=ft.Colors.BLACK, expand=True, padding=20, visible=True
        )

        def close_camera(_):
            camera_view.visible = False
            page.update()

        page.add(camera_view)
        page.update()

    def create_form_photo_section(title, key):
        img = ft.Image(src="", width=250, height=150, visible=False, border_radius=10, fit=ft.BoxFit.COVER)
        status = ft.Text("❌ Нет фото", color=ft.Colors.RED)
        form_photo_widgets[key] = {"img": img, "status": status}
        return ft.Container(
            content=ft.Column([
                ft.Text(title, weight=ft.FontWeight.BOLD, size=14),
                status, img,
                ft.Row([
                    ft.OutlinedButton("🖼️ Галерея", icon=ft.Icons.PHOTO_LIBRARY, on_click=lambda e: pick_gallery(e, key)),
                    ft.Button("📷 Камера", icon=ft.Icons.CAMERA_ALT, on_click=lambda e: open_camera(e, key))
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10, border=ft.Border.all(1, ft.Colors.GREY_300), border_radius=10, margin=ft.Margin.only(bottom=10)
        )

    # ==========================================
    # 1. ВКЛАДКА: НОВАЯ ЗАЯВКА
    # ==========================================
    field_style = {"width": 350, "height": 50}

    new_obj_name = ft.TextField(label="Наименование объекта", **field_style)
    new_district = ft.Dropdown(
        label="Район / Город",
        options=[
            ft.DropdownOption(key="grozny", text="Грозный"),
            ft.DropdownOption(key="argun", text="Аргун"),
            ft.DropdownOption(key="gudermes", text="Гудермес"),
            ft.DropdownOption(key="ur_mar", text="Урус-Мартан"),
            ft.DropdownOption(key="shali", text="Шали"),
            ft.DropdownOption(key="kurchaloy", text="Курчалой"),
            ft.DropdownOption(key="achhoy", text="Ачхой-Мартан"),
            ft.DropdownOption(key="oyshara", text="Ойсхара"),
            ft.DropdownOption(key="shelkovskaya", text="Шелковская"),
            ft.DropdownOption(key="naurskaya", text="Наурская"),
            ft.DropdownOption(key="sernovodskoe", text="Серноводское"),
        ], **field_style
    )
    new_address = ft.TextField(label="Адрес", **field_style)
    new_fio = ft.TextField(label="ФИО клиента", **field_style)
    new_created_by = ft.TextField(label="Специалист (создал заявку)", **field_style)

    new_meter = ft.Dropdown(
        label="Тип счетчика",
        options=[
            ft.DropdownOption(key="smt_smart_g6b", text="СМТ Смарт-К G6-B"),
            ft.DropdownOption(key="smt_smart_g4b", text="СМТ Смарт-К G4-B"),
            ft.DropdownOption(key="smt_smart_g10b", text="СМТ Смарт-К G10-B"),
            ft.DropdownOption(key="smt_comp_g16", text="СМТ Комплекс G16"),
            ft.DropdownOption(key="smt_comp_g25", text="СМТ Комплекс G25"),
            ft.DropdownOption(key="smt_comp_g40", text="СМТ Комплекс G40"),
            ft.DropdownOption(key="smt_comp_g65", text="СМТ Комплекс G65"),
            ft.DropdownOption(key="neo_g4", text="НЕО-G4"),
            ft.DropdownOption(key="neo_g6", text="НЕО-G6"),
            ft.DropdownOption(key="neo_g16", text="НЕО-G16"),
            ft.DropdownOption(key="neo_g10", text="НЕО-G10"),
            ft.DropdownOption(key="neo_g25", text="НЕО-G25"),
            ft.DropdownOption(key="mirk_51_g4", text="Миртек-51-РУ-G4"),
            ft.DropdownOption(key="mirk_51_g6", text="Миртек-51-РУ-G6"),
            ft.DropdownOption(key="mirk_51_g10", text="Миртек-51-РУ-G10"),
            ft.DropdownOption(key="mirk_51_g16", text="Миртек-51-РУ-G16"),
            ft.DropdownOption(key="mirk_51_g25", text="Миртек-51-РУ-G25"),
        ], **field_style
    )

    new_meter_serial = ft.TextField(label="Заводской номер", **field_style)
    new_meter_readings = ft.TextField(label="Показания", **field_style)
    new_meter_seal = ft.TextField(label="Номер пломбы", **field_style)
    new_malfunction = ft.TextField(label="Неисправность", multiline=True, min_lines=1, max_lines=3, width=350)

    def save_new_request(e):
        if not new_address.value or not new_fio.value:
            page.show_dialog(ft.SnackBar(ft.Text("Заполните Адрес и ФИО!"), bgcolor=ft.Colors.RED))
            return

        district_text = ""
        for opt in new_district.options:
            if opt.key == new_district.value:
                district_text = opt.text
                break

        meter_text = "Не указан"
        for opt in new_meter.options:
            if opt.key == new_meter.value:
                meter_text = opt.text
                break

        persisted_photos = {}
        for k, path in new_photo_paths.items():
            persisted_photos[k] = persist_photo(path, k) if path else None

        db.save_request({
            "obj_name": new_obj_name.value,
            "address": f"{district_text}, {new_address.value}" if district_text else new_address.value,
            "fio": new_fio.value,
            "meter": meter_text,
            "meter_serial": new_meter_serial.value,
            "meter_readings": new_meter_readings.value,
            "meter_seal": new_meter_seal.value,
            "malfunction": new_malfunction.value,
            "status": "active",
            "created_by": new_created_by.value if new_created_by.value else "Не указан",
            "repaired_by": "",
            "repair_process": "",
            "repair_parts": "",
            "repair_cost": "",
            "photos": persisted_photos,
        })

        # Очистка формы
        new_obj_name.value = ""
        new_district.value = None
        new_address.value = ""
        new_fio.value = ""
        new_meter.value = None
        new_meter_serial.value = ""
        new_meter_readings.value = ""
        new_meter_seal.value = ""
        new_malfunction.value = ""
        new_created_by.value = ""

        for k in new_photo_paths:
            new_photo_paths[k] = None
            form_photo_widgets[k]["img"].visible = False
            form_photo_widgets[k]["status"].value = "❌ Нет фото"
            form_photo_widgets[k]["status"].color = ft.Colors.RED

        refresh_lists()
        page.show_dialog(ft.SnackBar(ft.Text("✅ Заявка создана!"), bgcolor=ft.Colors.GREEN))
        tab_bar_view.selected_index = 1
        page.update()

    form_tab = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Создание новой заявки", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            new_obj_name, new_district, new_address, new_fio, new_created_by,
            ft.Divider(),
            ft.Text("Данные счетчика", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            new_meter, new_meter_serial, new_meter_readings, new_meter_seal, new_malfunction,
            ft.Divider(),
            ft.Text("Фотофиксация", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
            create_form_photo_section("1. Счетчик с показаниями", "meter"),
            create_form_photo_section("2. Заводской номер", "serial"),
            create_form_photo_section("3. Общее фото", "general"),
            create_form_photo_section("4. Фото объекта", "object"),
            create_form_photo_section("5. Фото пломбы", "seal"),
            ft.Container(height=10),
            ft.Button("Сохранить заявку", icon=ft.Icons.SAVE, on_click=save_new_request,
                      bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, width=350, height=50)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # ==========================================
    # ПОИСК
    # ==========================================
    def on_search_active(e):
        nonlocal search_query_active
        search_query_active = e.control.value.lower()
        refresh_lists()

    def on_search_completed(e):
        nonlocal search_query_completed
        search_query_completed = e.control.value.lower()
        refresh_lists()

    search_field_active = ft.TextField(label="Поиск по адресу, ФИО, зав. номеру...", prefix_icon=ft.Icons.SEARCH, on_change=on_search_active, margin=ft.Margin.only(left=10, right=10, top=10))
    search_field_completed = ft.TextField(label="Поиск по готовым заявкам...", prefix_icon=ft.Icons.SEARCH, on_change=on_search_completed, margin=ft.Margin.only(left=10, right=10, top=10))

    active_tab_wrapper = ft.Column([search_field_active, list_active], expand=True)
    completed_tab_wrapper = ft.Column([search_field_completed, list_completed], expand=True)

    tab_bar_view = ft.TabBarView(expand=True, controls=[form_tab, active_tab_wrapper, completed_tab_wrapper])

    main_tabs = ft.Tabs(
        selected_index=0, length=3, animation_duration=300, expand=True,
        content=ft.Column(expand=True, controls=[
            ft.TabBar(tabs=[ft.Tab(label="➕ Новая"), ft.Tab(label="🛠️ В работе"), ft.Tab(label="✅ Готовые")]),
            tab_bar_view
        ])
    )

    content_area = ft.Container(content=main_tabs, expand=True)

    def refresh_lists():
        list_active.controls.clear()
        list_completed.controls.clear()

        active_reqs = db.get_filtered_requests("active", search_query_active)
        completed_reqs = db.get_filtered_requests("completed", search_query_completed)

        for req in active_reqs + completed_reqs:
            card_controls = [
                ft.Text(f"Заявка №{req['id']} | {req['meter']}", weight=ft.FontWeight.BOLD),
                ft.Text(f"Зав. №: {req.get('meter_serial', 'Не указан')}", color=ft.Colors.GREY_700),
                ft.Text(f"Адрес: {req['address']}"),
                ft.Text(f"Клиент: {req['fio']}"),
                ft.Text(f"Создал: {req.get('created_by', 'Не указан')}", color=ft.Colors.BLUE),
                ft.Text("Статус: " + ("В работе" if req['status'] == 'active' else "Завершена"),
                        color=ft.Colors.ORANGE if req['status'] == 'active' else ft.Colors.GREEN)
            ]

            if req['status'] == 'completed':
                cost = req.get('repair_cost', '')
                worker = req.get('repaired_by', 'Не указан')
                if cost:
                    card_controls.append(ft.Text(f"💰 Стоимость: {cost} ₽", color=ft.Colors.GREEN_800, weight=ft.FontWeight.BOLD))
                card_controls.append(ft.Text(f"🔧 Выполнил: {worker}", color=ft.Colors.GREY_800))

            card = ft.Container(
                content=ft.Column(card_controls),
                padding=15, border=ft.Border.all(1, ft.Colors.GREY_300), border_radius=10, bgcolor=ft.Colors.WHITE,
                on_click=lambda e, r=req: open_request_detail(r, is_view_only=(r['status'] == 'completed')),
                ink=True
            )

            if req['status'] == 'active':
                list_active.controls.append(card)
            else:
                list_completed.controls.append(card)

        page.update()

    # ==========================================
    # ОКНО ПРОСМОТРА / РЕМОНТА ЗАЯВКИ
    # ==========================================
    def open_request_detail(req, is_view_only=False):
        repair_process = ft.TextField(label="Процесс ремонта", multiline=True, min_lines=2, value=req.get("repair_process", ""), read_only=is_view_only)
        repair_parts = ft.TextField(label="Замененные детали", multiline=True, min_lines=1, value=req.get("repair_parts", ""), read_only=is_view_only)
        repair_cost = ft.TextField(label="Стоимость (руб.)", value=req.get("repair_cost", ""), read_only=is_view_only)
        repair_worker = ft.TextField(label="Специалист (выполнил ремонт)", value=req.get("repaired_by", ""), read_only=is_view_only)

        def go_back(e):
            content_area.content = main_tabs
            page.update()

        def complete_repair(e):
            db.complete_request(int(req["id"]), {
                "repair_process": repair_process.value,
                "repair_parts": repair_parts.value,
                "repair_cost": repair_cost.value,
                "repaired_by": repair_worker.value if repair_worker.value else "Не указан",
            })
            refresh_lists()
            go_back(None)

        # --- ЛОГИКА PDF ---
        def export_pdf(e):
            try:
                path = generate_request_pdf(req)
            except Exception as ex:
                page.show_dialog(ft.SnackBar(ft.Text(f"Ошибка PDF: {ex}"), bgcolor=ft.Colors.RED))
                return
            try:
                if os.name == "nt":
                    os.startfile(path)  # type: ignore[attr-defined]
                    page.show_dialog(ft.SnackBar(ft.Text("✅ PDF сформирован и открыт")))
                else:
                    page.show_dialog(ft.SnackBar(ft.Text(f"✅ PDF сохранён: {path}")))
            except Exception:
                page.show_dialog(ft.SnackBar(ft.Text(f"✅ PDF сохранён: {path}")))

        # --- ЛОГИКА TELEGRAM ---
        def send_tg(e):
            try:
                path = generate_request_pdf(req)
            except Exception as ex:
                page.show_dialog(ft.SnackBar(ft.Text(f"Ошибка PDF: {ex}"), bgcolor=ft.Colors.RED))
                return

            tg_button.text = "⏳ Отправка..."
            tg_button.disabled = True
            page.update()

            def do_send():
                success, msg = send_pdf_to_telegram(path, req)
                tg_button.text = "📤 В Telegram"
                tg_button.disabled = False
                if success:
                    page.show_dialog(ft.SnackBar(ft.Text("✅ PDF отправлен в Telegram!"), bgcolor=ft.Colors.GREEN))
                else:
                    page.show_dialog(ft.SnackBar(ft.Text(f"❌ Ошибка: {msg}"), bgcolor=ft.Colors.RED))
                page.update()

            page.run_thread(do_send)

        # --- СОЗДАНИЕ КНОПОК ---
        pdf_button = ft.Button("📄 Экспорт в PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf, bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        tg_button = ft.Button("📤 В Telegram", icon=ft.Icons.SEND, on_click=send_tg, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)

        if is_view_only:
            action_buttons = ft.Row([
                pdf_button,
                tg_button,
                ft.Button("✏️ Редактировать", icon=ft.Icons.EDIT, bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE, on_click=lambda _: open_request_detail(req, is_view_only=False))
            ], alignment=ft.MainAxisAlignment.CENTER, wrap=True)
        else:
            action_buttons = ft.Row([
                pdf_button,
                tg_button,
                ft.Button("✅ Завершить ремонт", icon=ft.Icons.CHECK, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=complete_repair)
            ], alignment=ft.MainAxisAlignment.CENTER, wrap=True)

        photos_column = ft.Column(spacing=10)
        photo_titles = {"meter": "1. Счетчик с показаниями", "serial": "2. Заводской номер", "general": "3. Общее фото", "object": "4. Фото объекта", "seal": "5. Фото пломбы"}

        for k, title in photo_titles.items():
            path = req["photos"].get(k)
            if path and os.path.exists(path):
                photos_column.controls.append(ft.Column([
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=12),
                    ft.Image(src=path, width=250, height=150, border_radius=10, fit=ft.BoxFit.COVER)
                ]))
            else:
                photos_column.controls.append(ft.Text(f"{title}: ❌ Нет фото", color=ft.Colors.RED, size=12))

        detail_view = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), ft.Text(f"Заявка №{req['id']}", size=20, weight=ft.FontWeight.BOLD)]),
            ft.Divider(),

            ft.Text("Данные объекта", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ft.Text(f"Объект: {req.get('obj_name', 'Не указан')}"),
            ft.Text(f"Адрес: {req['address']}"),
            ft.Text(f"Клиент: {req['fio']}"),
            ft.Text(f"Создал заявку: {req.get('created_by', 'Не указан')}", color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text("Данные счетчика", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ft.Text(f"Тип: {req['meter']}"),
            ft.Text(f"Заводской номер: {req.get('meter_serial', 'Не указан')}"),
            ft.Text(f"Показания: {req.get('meter_readings', 'Не указан')}"),
            ft.Text(f"Номер пломбы: {req.get('meter_seal', 'Не указан')}"),
            ft.Text(f"Неисправность: {req.get('malfunction', 'Нет')}"),
            ft.Divider(),

            ft.Text("Фотофиксация", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            photos_column,
            ft.Divider(),

            ft.Text("Выполнение ремонта", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700),
            repair_worker, repair_process, repair_parts, repair_cost,
            ft.Container(height=20),
            action_buttons
        ], scroll=ft.ScrollMode.AUTO)

        content_area.content = ft.Container(content=detail_view, padding=20)
        page.update()

    page.add(content_area)
    refresh_lists()


if __name__ == "__main__":
    ft.run(main)