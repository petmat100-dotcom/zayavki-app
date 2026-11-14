# database.py
import os
from supabase import create_client, Client

# Заглушки, которые заменятся при сборке
URL = "SUPABASE_URL_PLACEHOLDER"
KEY = "SUPABASE_KEY_PLACEHOLDER"

def get_client():
    if "PLACEHOLDER" in URL:
        print("ОШИБКА: Секреты Supabase не подгрузились!")
    return create_client(URL, KEY)
def init_db():
    # Таблица уже создана в Supabase через SQL Editor
    pass

def save_request(data: dict) -> int:
    supabase = get_client()
    photos = data.get("photos", {})
    
    db_data = {
        "obj_name": data.get("obj_name"),
        "address": data.get("address"),
        "fio": data.get("fio"),
        "meter": data.get("meter"),
        "meter_serial": data.get("meter_serial"),
        "meter_readings": data.get("meter_readings"),
        "meter_seal": data.get("meter_seal"),
        "malfunction": data.get("malfunction"),
        "status": data.get("status", "active"),
        "created_by": data.get("created_by"),
        "repaired_by": data.get("repaired_by", ""),
        "repair_process": data.get("repair_process", ""),
        "repair_parts": data.get("repair_parts", ""),
        "repair_cost": data.get("repair_cost", ""),
        "photo_meter": photos.get("meter"),
        "photo_serial": photos.get("serial"),
        "photo_general": photos.get("general"),
        "photo_object": photos.get("object"),
        "photo_seal": photos.get("seal"),
    }
    
    response = supabase.table("requests").insert(db_data).execute()
    return response.data[0]['id'] if response.data else 0

def complete_request(request_id: int, data: dict):
    supabase = get_client()
    supabase.table("requests").update({
        "status": "completed",
        "repair_process": data.get("repair_process", ""),
        "repair_parts": data.get("repair_parts", ""),
        "repair_cost": data.get("repair_cost", ""),
        "repaired_by": data.get("repaired_by", ""),
    }).eq("id", request_id).execute()

def get_filtered_requests(status: str, search_query: str = "") -> list:
    supabase = get_client()
    response = supabase.table("requests").select("*").eq("status", status).order("id", desc=True).execute()
    requests = response.data
    
    if search_query:
        pattern = search_query.lower()
        filtered = []
        for r in requests:
            if (pattern in (r.get("address") or "").lower() or
                pattern in (r.get("fio") or "").lower() or
                pattern in (r.get("meter_serial") or "").lower() or
                pattern in (r.get("obj_name") or "").lower()):
                filtered.append(r)
        requests = filtered

    result = []
    for row in requests:
        result.append({
            "id": row["id"], "obj_name": row["obj_name"] or "", "address": row["address"] or "",
            "fio": row["fio"] or "", "meter": row["meter"] or "", "meter_serial": row["meter_serial"] or "",
            "meter_readings": row["meter_readings"] or "", "meter_seal": row["meter_seal"] or "",
            "malfunction": row["malfunction"] or "", "status": row["status"], "created_by": row["created_by"] or "",
            "repaired_by": row["repaired_by"] or "", "repair_process": row["repair_process"] or "",
            "repair_parts": row["repair_parts"] or "", "repair_cost": row["repair_cost"] or "",
            "photos": {
                "meter": row["photo_meter"], "serial": row["photo_serial"], "general": row["photo_general"],
                "object": row["photo_object"], "seal": row["photo_seal"],
            },
        })
    return result
