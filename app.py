import json
import logging
import os
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request

try:
    import firebase_admin
    from google.cloud.firestore_v1 import FieldFilter
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    FieldFilter = None
    credentials = None
    firestore = None


load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "appointments.json")
SOURCE_NAME = "Sumitra Hospital OPD timetable"
PHONE_PATTERN = re.compile(r"^\d{10}$")
VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FIREBASE_CLIENT = None
FIREBASE_INIT_ERROR = None

SUMITRA_DOCTOR_SCHEDULE = [
    {
        "name": "Dr. Rajesh Goel",
        "specialty": "Nephrology",
        "days": ["Sunday"],
        "startTime": "11:00 AM",
        "endTime": "12:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Somya Agarwal",
        "specialty": "Gastroenterology",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "startTime": "10:00 AM",
        "endTime": "12:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Ayushi Agarwal",
        "specialty": "Cardiology",
        "days": ["Monday", "Wednesday", "Friday"],
        "startTime": "5:00 PM",
        "endTime": "6:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Vikas Bansal",
        "specialty": "Urology",
        "days": ["Monday", "Wednesday", "Friday"],
        "startTime": "5:00 PM",
        "endTime": "6:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Rekha Mittal",
        "specialty": "Paediatric Neurology",
        "days": ["Monday", "Friday"],
        "startTime": "3:00 PM",
        "endTime": "4:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Shazia Zaidi",
        "specialty": "Dermatology & Venereology",
        "days": ["Tuesday", "Thursday", "Saturday"],
        "startTime": "12:00 PM",
        "endTime": "1:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Neha Saini",
        "specialty": "Dental",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "startTime": "10:00 AM",
        "endTime": "6:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Jyoti Bhatia",
        "specialty": "Physiotherapy",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "startTime": "10:00 AM",
        "endTime": "5:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Nitin Kumar Rai",
        "specialty": "Neurology",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "startTime": "9:00 AM",
        "endTime": "10:00 AM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Alok Sharma",
        "specialty": "Ophthalmology",
        "days": ["Monday", "Wednesday", "Friday", "Saturday"],
        "startTime": "10:00 AM",
        "endTime": "12:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Alok Sharma",
        "specialty": "Ophthalmology",
        "days": ["Tuesday", "Thursday"],
        "startTime": "2:00 PM",
        "endTime": "4:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Kalpana Upamanyu",
        "specialty": "Psychology",
        "days": ["Monday", "Wednesday", "Friday"],
        "startTime": "12:00 PM",
        "endTime": "2:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. A. K. Arora",
        "specialty": "Respiratory Medicine",
        "days": [],
        "startTime": "",
        "endTime": "",
        "availabilityType": "On Prior Appointment",
    },
    {
        "name": "Dr. Naman Utreja",
        "specialty": "Oncology",
        "days": [],
        "startTime": "",
        "endTime": "",
        "availabilityType": "On Prior Appointment",
    },
    {
        "name": "Dr. Ashwani Mishra",
        "specialty": "Paediatrics Surgery",
        "days": ["Monday", "Thursday"],
        "startTime": "6:00 PM",
        "endTime": "7:00 PM",
        "availabilityType": "Scheduled",
    },
    {
        "name": "Dr. Hemant Kumar",
        "specialty": "Neuro Surgery",
        "days": [],
        "startTime": "",
        "endTime": "",
        "availabilityType": "On Prior Appointment",
    },
]


class BookingConflict(Exception):
    pass


class SlotNotFound(Exception):
    pass


def utc_now():
    return datetime.utcnow().isoformat() + "Z"


def normalize_text(value):
    return str(value or "").strip()


def normalize_key(value):
    return normalize_text(value).casefold()


def slugify(value):
    value = normalize_key(value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_day(day):
    day_key = normalize_key(day)
    for valid_day in VALID_DAYS:
        if day_key == valid_day.casefold():
            return valid_day
    return None


def parse_time(time_text):
    if not isinstance(time_text, str):
        return None

    cleaned_time = time_text.strip().upper()
    for time_format in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(cleaned_time, time_format)
        except ValueError:
            continue
    return None


def format_time(time_text):
    parsed_time = parse_time(time_text)
    if parsed_time is None:
        return None
    return parsed_time.strftime("%I:%M %p").lstrip("0")


def time_sort_key(time_text):
    parsed_time = parse_time(time_text)
    return parsed_time.time() if parsed_time else datetime.max.time()


def is_valid_phone(phone):
    return isinstance(phone, str) and PHONE_PATTERN.match(phone.strip()) is not None


def json_error(message, status_code=400, details=None):
    response = {"success": False, "error": message}
    if details is not None:
        response["details"] = details
    return jsonify(response), status_code


def parse_tool_arguments(arguments):
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def get_request_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}

    parsed_arguments = parse_tool_arguments(data.get("arguments"))
    if parsed_arguments:
        return parsed_arguments

    message = data.get("message")
    if isinstance(message, dict):
        tool_calls = message.get("toolCalls")
        if isinstance(tool_calls, list) and tool_calls:
            function_data = tool_calls[0].get("function", {})
            parsed_arguments = parse_tool_arguments(function_data.get("arguments"))
            if parsed_arguments:
                return parsed_arguments

    return data


def load_local_database():
    if not os.path.exists(DB_FILE):
        return {"doctors": [], "appointments": []}

    with open(DB_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "appointments" in data and "doctors" in data:
        return data

    return {"doctors": [], "appointments": []}


def save_local_database(data):
    with open(DB_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def get_firebase_client():
    global FIREBASE_CLIENT, FIREBASE_INIT_ERROR

    if FIREBASE_CLIENT is not None:
        return FIREBASE_CLIENT

    credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not credentials_json:
        FIREBASE_INIT_ERROR = "FIREBASE_CREDENTIALS_JSON is missing. Using appointments.json fallback."
        return None

    if firebase_admin is None:
        FIREBASE_INIT_ERROR = "firebase-admin is not installed. Run pip install -r requirements.txt."
        return None

    try:
        credentials_dict = json.loads(credentials_json)
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_dict)
            firebase_admin.initialize_app(cred)
        FIREBASE_CLIENT = firestore.client()
        FIREBASE_INIT_ERROR = None
        return FIREBASE_CLIENT
    except Exception as error:
        FIREBASE_INIT_ERROR = f"Firebase initialization failed: {error}"
        logger.exception("Firebase initialization failed")
        return None


def using_firestore():
    return get_firebase_client() is not None


def apply_firestore_filter(query, field_path, op_string, value):
    if FieldFilter is not None:
        return query.where(filter=FieldFilter(field_path, op_string, value))
    return query.where(field_path, op_string, value)


def schedule_doc_id(schedule):
    return "doctor_" + slugify(
        f"{schedule['name']}_{schedule['specialty']}_{','.join(schedule['days'])}_{schedule['startTime']}_{schedule['endTime']}"
    )


def slot_doc_id(doctor, specialty, day, time_text):
    return "slot_" + slugify(f"{doctor}_{specialty}_{day}_{time_text}")


def iter_slot_times(start_time, end_time):
    start = parse_time(start_time)
    end = parse_time(end_time)
    if not start or not end or start >= end:
        return []

    times = []
    current = start
    while current < end:
        times.append(current.strftime("%I:%M %p").lstrip("0"))
        current += timedelta(hours=1)
    return times


def build_doctor_documents():
    doctors = []
    for schedule in SUMITRA_DOCTOR_SCHEDULE:
        doctor = {
            **schedule,
            "doctor_id": schedule_doc_id(schedule),
            "name_lower": normalize_key(schedule["name"]),
            "specialty_lower": normalize_key(schedule["specialty"]),
            "source": SOURCE_NAME,
        }
        doctors.append(doctor)
    return doctors


def build_slot_documents():
    slots = []
    for schedule in SUMITRA_DOCTOR_SCHEDULE:
        if schedule["availabilityType"] != "Scheduled":
            continue
        for day in schedule["days"]:
            for slot_time in iter_slot_times(schedule["startTime"], schedule["endTime"]):
                appointment_id = slot_doc_id(schedule["name"], schedule["specialty"], day, slot_time)
                slots.append(
                    {
                        "appointment_id": appointment_id,
                        "doctor": schedule["name"],
                        "doctor_lower": normalize_key(schedule["name"]),
                        "specialty": schedule["specialty"],
                        "specialty_lower": normalize_key(schedule["specialty"]),
                        "day": day,
                        "time": slot_time,
                        "patient_name": "",
                        "phone": "",
                        "reason": "",
                        "status": "Available",
                        "booked_at": "",
                        "cancelled_at": "",
                        "rescheduled_at": "",
                        "availabilityType": schedule["availabilityType"],
                        "source": SOURCE_NAME,
                    }
                )
    return slots


def seed_local_data():
    doctors = build_doctor_documents()
    existing_data = load_local_database()
    existing_slots = {
        item.get("appointment_id"): item
        for item in existing_data.get("appointments", [])
        if item.get("appointment_id")
    }

    slots = []
    for slot in build_slot_documents():
        existing_slot = existing_slots.get(slot["appointment_id"])
        if existing_slot and existing_slot.get("status") == "Booked":
            slots.append(existing_slot)
        else:
            slots.append(slot)

    data = {"doctors": doctors, "appointments": slots}
    save_local_database(data)
    return {"doctor_count": len(doctors), "slot_count": len(slots), "database": "appointments.json"}


def ensure_local_data():
    data = load_local_database()
    if not data.get("doctors") or not data.get("appointments"):
        seed_local_data()
        data = load_local_database()
    return data


def sanitize_slot(slot, include_patient=False):
    response = {
        "appointment_id": slot.get("appointment_id", ""),
        "doctor": slot.get("doctor", ""),
        "specialty": slot.get("specialty", ""),
        "day": slot.get("day", ""),
        "time": slot.get("time", ""),
        "status": slot.get("status", ""),
        "source": slot.get("source", SOURCE_NAME),
    }
    if include_patient:
        response.update(
            {
                "patient_name": slot.get("patient_name", ""),
                "phone": slot.get("phone", ""),
                "reason": slot.get("reason", ""),
                "booked_at": slot.get("booked_at", ""),
                "cancelled_at": slot.get("cancelled_at", ""),
                "rescheduled_at": slot.get("rescheduled_at", ""),
            }
        )
    return response


def sort_slots(slots):
    return sorted(slots, key=lambda item: (item.get("day", ""), time_sort_key(item.get("time", "")), item.get("doctor", "")))


def seed_firestore_data(client):
    doctors = build_doctor_documents()
    slots = build_slot_documents()
    seeded_doctors = 0
    seeded_slots = 0

    batch = client.batch()
    pending_writes = 0

    for doctor in doctors:
        ref = client.collection("doctors").document(doctor["doctor_id"])
        batch.set(ref, doctor, merge=True)
        pending_writes += 1
        seeded_doctors += 1

    for slot in slots:
        ref = client.collection("appointments").document(slot["appointment_id"])
        existing = ref.get()
        if existing.exists:
            current = existing.to_dict() or {}
            update_data = {
                "doctor": slot["doctor"],
                "doctor_lower": slot["doctor_lower"],
                "specialty": slot["specialty"],
                "specialty_lower": slot["specialty_lower"],
                "day": slot["day"],
                "time": slot["time"],
                "availabilityType": slot["availabilityType"],
                "source": SOURCE_NAME,
            }
            if current.get("status") not in {"Booked", "Available"}:
                update_data.update(slot)
            batch.set(ref, update_data, merge=True)
        else:
            batch.set(ref, slot)
        pending_writes += 1
        seeded_slots += 1

        if pending_writes >= 450:
            batch.commit()
            batch = client.batch()
            pending_writes = 0

    if pending_writes:
        batch.commit()

    return {"doctor_count": seeded_doctors, "slot_count": seeded_slots, "database": "Firestore"}


def seed_secret_is_valid(data):
    expected_key = os.environ.get("SEED_SECRET_KEY")
    if not expected_key:
        return False

    provided_key = (
        request.headers.get("X-Seed-Key")
        or request.headers.get("x-seed-key")
        or request.args.get("key")
        or normalize_text(data.get("seed_secret_key"))
    )
    return provided_key == expected_key


def firestore_slots_for_query(client, day=None, specialty=None, doctor=None, status=None):
    query = client.collection("appointments")
    if day:
        query = apply_firestore_filter(query, "day", "==", day)
    elif status:
        query = apply_firestore_filter(query, "status", "==", status)

    specialty_key = normalize_key(specialty)
    doctor_key = normalize_key(doctor)
    slots = []

    for doc in query.stream():
        slot = doc.to_dict() or {}
        slot["appointment_id"] = doc.id
        if status and slot.get("status") != status:
            continue
        if specialty_key and normalize_key(slot.get("specialty")) != specialty_key:
            continue
        if doctor_key and normalize_key(slot.get("doctor")) != doctor_key:
            continue
        slots.append(slot)

    return sort_slots(slots)


def local_slots_for_query(day=None, specialty=None, doctor=None, status=None):
    data = ensure_local_data()
    specialty_key = normalize_key(specialty)
    doctor_key = normalize_key(doctor)

    slots = []
    for slot in data.get("appointments", []):
        if day and slot.get("day") != day:
            continue
        if status and slot.get("status") != status:
            continue
        if specialty_key and normalize_key(slot.get("specialty")) != specialty_key:
            continue
        if doctor_key and normalize_key(slot.get("doctor")) != doctor_key:
            continue
        slots.append(slot)
    return sort_slots(slots)


def prior_appointment_doctors(specialty=None):
    specialty_key = normalize_key(specialty)
    doctors = []
    for doctor in build_doctor_documents():
        if doctor.get("availabilityType") != "On Prior Appointment":
            continue
        if specialty_key and normalize_key(doctor.get("specialty")) != specialty_key:
            continue
        doctors.append(
            {
                "doctor": doctor["name"],
                "specialty": doctor["specialty"],
                "availabilityType": doctor["availabilityType"],
                "source": doctor["source"],
            }
        )
    return doctors


def find_firestore_slot(client, doctor, specialty, day, time_text):
    slots = firestore_slots_for_query(client, day=day, specialty=specialty, doctor=doctor)
    for slot in slots:
        if slot.get("time") == time_text:
            return client.collection("appointments").document(slot["appointment_id"]), slot
    return None, None


def find_local_slot(data, doctor, specialty, day, time_text):
    doctor_key = normalize_key(doctor)
    specialty_key = normalize_key(specialty)
    for index, slot in enumerate(data.get("appointments", [])):
        if (
            normalize_key(slot.get("doctor")) == doctor_key
            and normalize_key(slot.get("specialty")) == specialty_key
            and slot.get("day") == day
            and slot.get("time") == time_text
        ):
            return index, slot
    return None, None


def find_active_local_appointment(data, appointment_id=None, phone=None):
    matches = []
    for index, slot in enumerate(data.get("appointments", [])):
        if slot.get("status") != "Booked":
            continue
        if appointment_id and slot.get("appointment_id") == appointment_id:
            return [(index, slot)]
        if phone and slot.get("phone") == phone:
            matches.append((index, slot))
    return matches


def find_active_firestore_appointment(client, appointment_id=None, phone=None):
    if appointment_id:
        ref = client.collection("appointments").document(appointment_id)
        snapshot = ref.get()
        if snapshot.exists:
            slot = snapshot.to_dict() or {}
            slot["appointment_id"] = snapshot.id
            if slot.get("status") == "Booked":
                return [(ref, slot)]
        return []

    if phone:
        query = apply_firestore_filter(client.collection("appointments"), "phone", "==", phone)
        matches = []
        for doc in query.stream():
            slot = doc.to_dict() or {}
            if slot.get("status") != "Booked":
                continue
            slot["appointment_id"] = doc.id
            matches.append((client.collection("appointments").document(doc.id), slot))
        return matches

    return []


def appointment_lookup_error(matches):
    if not matches:
        return json_error("No active booked appointment found.", 404)
    if len(matches) > 1:
        return json_error(
            "Multiple active appointments found. Please provide appointment_id.",
            409,
            {"appointments": [sanitize_slot(slot, include_patient=True) for _, slot in matches]},
        )
    return None


def validate_booking_payload(data):
    name = normalize_text(data.get("name") or data.get("patient_name"))
    phone = normalize_text(data.get("phone"))
    doctor = normalize_text(data.get("doctor"))
    specialty = normalize_text(data.get("specialty"))
    day = normalize_day(data.get("day"))
    appointment_time = format_time(data.get("time"))
    reason = normalize_text(data.get("reason")) or "General consultation"

    if not name:
        return None, json_error("Patient name is required.", 400)
    if not is_valid_phone(phone):
        return None, json_error("Invalid phone. Phone number must be exactly 10 digits.", 400)
    if not doctor:
        return None, json_error("Doctor name is required.", 400)
    if not specialty:
        return None, json_error("Specialty is required.", 400)
    if not day:
        return None, json_error("Invalid day. Please choose a valid OPD day.", 400)
    if not appointment_time:
        return None, json_error("Invalid time format. Use values like 5:00 PM.", 400)

    return {
        "name": name,
        "phone": phone,
        "doctor": doctor,
        "specialty": specialty,
        "day": day,
        "time": appointment_time,
        "reason": reason,
    }, None


@app.errorhandler(404)
def not_found(_error):
    return json_error("Endpoint not found.", 404)


@app.errorhandler(405)
def method_not_allowed(_error):
    return json_error("Method not allowed for this endpoint.", 405)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.exception("Unexpected server error: %s", error)
    return json_error("Internal server error.", 500)


@app.get("/health")
def health_check():
    client = get_firebase_client()
    return jsonify(
        {
            "success": True,
            "status": "ok",
            "database": "Firestore" if client else "appointments.json fallback",
            "firebase_configured": client is not None,
            "firebase_message": FIREBASE_INIT_ERROR or "Firebase connected.",
        }
    ), 200


@app.post("/seed-data")
def seed_data():
    data = get_request_data()
    if not seed_secret_is_valid(data):
        logger.warning("Rejected /seed-data request because SEED_SECRET_KEY was missing or invalid.")
        return json_error("Invalid or missing seed secret key.", 400)

    client = get_firebase_client()
    if client:
        result = seed_firestore_data(client)
    else:
        result = seed_local_data()

    logger.info("Seeded Sumitra Hospital OPD data into %s", result["database"])
    return jsonify(
        {
            "success": True,
            "message": "Sumitra Hospital OPD timetable seeded successfully.",
            **result,
            "source": SOURCE_NAME,
        }
    ), 200


@app.post("/check-availability")
def check_availability():
    data = get_request_data()
    day = normalize_day(data.get("day"))
    specialty = normalize_text(data.get("specialty"))

    if not day:
        return json_error("Invalid day. Please choose a valid OPD day.", 400)

    client = get_firebase_client()
    if client:
        slots = firestore_slots_for_query(client, day=day, specialty=specialty, status="Available")
    else:
        slots = local_slots_for_query(day=day, specialty=specialty, status="Available")

    available_slots = [sanitize_slot(slot) for slot in slots]
    return jsonify(
        {
            "success": True,
            "day": day,
            "specialty": specialty or None,
            "available_slots": available_slots,
            "prior_appointment_doctors": prior_appointment_doctors(specialty),
            "is_available": bool(available_slots),
        }
    ), 200


@app.post("/book-appointment")
def book_appointment():
    data = get_request_data()
    payload, validation_error = validate_booking_payload(data)
    if validation_error:
        return validation_error

    client = get_firebase_client()
    now = utc_now()

    if client:
        slot_ref, slot = find_firestore_slot(
            client,
            payload["doctor"],
            payload["specialty"],
            payload["day"],
            payload["time"],
        )
        if not slot_ref:
            return json_error("No matching available OPD slot found for this doctor, specialty, day, and time.", 404)

        transaction = client.transaction()

        @firestore.transactional
        def book_in_transaction(transaction, ref):
            snapshot = ref.get(transaction=transaction)
            current = snapshot.to_dict() or {}
            if current.get("status") == "Booked":
                raise BookingConflict("Requested slot is already booked.")
            if current.get("status") != "Available":
                raise SlotNotFound("Requested slot is not available.")

            update_data = {
                "patient_name": payload["name"],
                "phone": payload["phone"],
                "reason": payload["reason"],
                "status": "Booked",
                "booked_at": now,
                "cancelled_at": "",
                "rescheduled_at": "",
            }
            transaction.update(ref, update_data)
            current.update(update_data)
            current["appointment_id"] = ref.id
            return current

        try:
            booked_slot = book_in_transaction(transaction, slot_ref)
        except BookingConflict:
            return json_error("Requested slot is already booked.", 409)
        except SlotNotFound:
            return json_error("Requested slot is not available.", 404)

    else:
        local_data = ensure_local_data()
        index, slot = find_local_slot(local_data, payload["doctor"], payload["specialty"], payload["day"], payload["time"])
        if slot is None:
            return json_error("No matching available OPD slot found for this doctor, specialty, day, and time.", 404)
        if slot.get("status") == "Booked":
            return json_error("Requested slot is already booked.", 409)
        if slot.get("status") != "Available":
            return json_error("Requested slot is not available.", 404)

        slot.update(
            {
                "patient_name": payload["name"],
                "phone": payload["phone"],
                "reason": payload["reason"],
                "status": "Booked",
                "booked_at": now,
                "cancelled_at": "",
                "rescheduled_at": "",
            }
        )
        local_data["appointments"][index] = slot
        save_local_database(local_data)
        booked_slot = slot

    logger.info("Booked appointment %s for %s", booked_slot.get("appointment_id"), payload["phone"])
    return jsonify(
        {
            "success": True,
            "message": "Appointment booked successfully.",
            "appointment": sanitize_slot(booked_slot, include_patient=True),
        }
    ), 201


@app.post("/cancel-appointment")
def cancel_appointment():
    data = get_request_data()
    appointment_id = normalize_text(data.get("appointment_id"))
    phone = normalize_text(data.get("phone"))

    if not appointment_id and not is_valid_phone(phone):
        return json_error("Provide appointment_id or a valid 10-digit phone number.", 400)

    client = get_firebase_client()
    now = utc_now()

    if client:
        matches = find_active_firestore_appointment(client, appointment_id=appointment_id, phone=phone)
        lookup_error = appointment_lookup_error(matches)
        if lookup_error:
            return lookup_error

        ref, slot = matches[0]
        ref.update(
            {
                "patient_name": "",
                "phone": "",
                "reason": "",
                "status": "Available",
                "booked_at": "",
                "cancelled_at": now,
            }
        )
        slot.update({"status": "Available", "patient_name": "", "phone": "", "reason": "", "booked_at": "", "cancelled_at": now})

    else:
        local_data = ensure_local_data()
        matches = find_active_local_appointment(local_data, appointment_id=appointment_id, phone=phone)
        lookup_error = appointment_lookup_error(matches)
        if lookup_error:
            return lookup_error

        index, slot = matches[0]
        slot.update(
            {
                "patient_name": "",
                "phone": "",
                "reason": "",
                "status": "Available",
                "booked_at": "",
                "cancelled_at": now,
            }
        )
        local_data["appointments"][index] = slot
        save_local_database(local_data)

    logger.info("Cancelled appointment %s", slot.get("appointment_id"))
    return jsonify(
        {
            "success": True,
            "message": "Appointment cancelled successfully.",
            "appointment": sanitize_slot(slot, include_patient=True),
        }
    ), 200


@app.post("/reschedule-appointment")
def reschedule_appointment():
    data = get_request_data()
    appointment_id = normalize_text(data.get("appointment_id"))
    phone = normalize_text(data.get("phone"))
    new_doctor = normalize_text(data.get("new_doctor") or data.get("doctor"))
    new_specialty = normalize_text(data.get("new_specialty") or data.get("specialty"))
    new_day = normalize_day(data.get("new_day") or data.get("day"))
    new_time = format_time(data.get("new_time") or data.get("time"))
    now = utc_now()

    if not appointment_id and not is_valid_phone(phone):
        return json_error("Provide appointment_id or a valid 10-digit phone number.", 400)
    if not new_day:
        return json_error("Invalid new day. Please choose a valid OPD day.", 400)
    if not new_time:
        return json_error("Invalid new time format. Use values like 5:00 PM.", 400)

    client = get_firebase_client()

    if client:
        matches = find_active_firestore_appointment(client, appointment_id=appointment_id, phone=phone)
        lookup_error = appointment_lookup_error(matches)
        if lookup_error:
            return lookup_error

        old_ref, old_slot = matches[0]
        target_doctor = new_doctor or old_slot["doctor"]
        target_specialty = new_specialty or old_slot["specialty"]
        new_ref, new_slot = find_firestore_slot(client, target_doctor, target_specialty, new_day, new_time)
        if not new_ref:
            return json_error("New slot was not found for the requested doctor, specialty, day, and time.", 404)
        if new_ref.id == old_ref.id:
            return json_error("New slot is the same as the current appointment.", 400)

        transaction = client.transaction()

        @firestore.transactional
        def reschedule_in_transaction(transaction, current_ref, target_ref):
            current_snapshot = current_ref.get(transaction=transaction)
            target_snapshot = target_ref.get(transaction=transaction)
            current_slot = current_snapshot.to_dict() or {}
            target_slot = target_snapshot.to_dict() or {}

            if current_slot.get("status") != "Booked":
                raise SlotNotFound("Current appointment is not active.")
            if target_slot.get("status") == "Booked":
                raise BookingConflict("Requested new slot is already booked.")
            if target_slot.get("status") != "Available":
                raise SlotNotFound("Requested new slot is not available.")

            patient_data = {
                "patient_name": current_slot.get("patient_name", ""),
                "phone": current_slot.get("phone", ""),
                "reason": current_slot.get("reason", ""),
                "status": "Booked",
                "booked_at": now,
                "cancelled_at": "",
                "rescheduled_at": now,
            }
            transaction.update(
                current_ref,
                {
                    "patient_name": "",
                    "phone": "",
                    "reason": "",
                    "status": "Available",
                    "booked_at": "",
                    "rescheduled_at": now,
                },
            )
            transaction.update(target_ref, patient_data)
            target_slot.update(patient_data)
            current_slot["appointment_id"] = current_ref.id
            target_slot["appointment_id"] = target_ref.id
            return current_slot, target_slot

        try:
            old_slot, new_slot = reschedule_in_transaction(transaction, old_ref, new_ref)
        except BookingConflict:
            return json_error("Requested new slot is already booked.", 409)
        except SlotNotFound as error:
            return json_error(str(error), 404)

    else:
        local_data = ensure_local_data()
        matches = find_active_local_appointment(local_data, appointment_id=appointment_id, phone=phone)
        lookup_error = appointment_lookup_error(matches)
        if lookup_error:
            return lookup_error

        old_index, old_slot = matches[0]
        target_doctor = new_doctor or old_slot["doctor"]
        target_specialty = new_specialty or old_slot["specialty"]
        new_index, new_slot = find_local_slot(local_data, target_doctor, target_specialty, new_day, new_time)
        if new_slot is None:
            return json_error("New slot was not found for the requested doctor, specialty, day, and time.", 404)
        if new_slot.get("appointment_id") == old_slot.get("appointment_id"):
            return json_error("New slot is the same as the current appointment.", 400)
        if new_slot.get("status") == "Booked":
            return json_error("Requested new slot is already booked.", 409)
        if new_slot.get("status") != "Available":
            return json_error("Requested new slot is not available.", 404)

        patient_data = {
            "patient_name": old_slot.get("patient_name", ""),
            "phone": old_slot.get("phone", ""),
            "reason": old_slot.get("reason", ""),
            "status": "Booked",
            "booked_at": now,
            "cancelled_at": "",
            "rescheduled_at": now,
        }
        old_slot.update({"patient_name": "", "phone": "", "reason": "", "status": "Available", "booked_at": "", "rescheduled_at": now})
        new_slot.update(patient_data)
        local_data["appointments"][old_index] = old_slot
        local_data["appointments"][new_index] = new_slot
        save_local_database(local_data)

    logger.info("Rescheduled appointment from %s to %s", old_slot.get("appointment_id"), new_slot.get("appointment_id"))
    return jsonify(
        {
            "success": True,
            "message": "Appointment rescheduled successfully.",
            "old_slot": sanitize_slot(old_slot, include_patient=True),
            "new_appointment": sanitize_slot(new_slot, include_patient=True),
        }
    ), 200


@app.post("/get-alternate-slots")
def get_alternate_slots():
    data = get_request_data()
    day = normalize_day(data.get("day")) if data.get("day") else None
    specialty = normalize_text(data.get("specialty"))
    doctor = normalize_text(data.get("doctor"))
    requested_time = format_time(data.get("time")) if data.get("time") else None

    if data.get("day") and not day:
        return json_error("Invalid day. Please choose a valid OPD day.", 400)
    if data.get("time") and not requested_time:
        return json_error("Invalid time format. Use values like 5:00 PM.", 400)

    client = get_firebase_client()
    if client:
        slots = firestore_slots_for_query(client, specialty=specialty, doctor=doctor, status="Available")
    else:
        slots = local_slots_for_query(specialty=specialty, doctor=doctor, status="Available")

    alternatives = []
    for slot in slots:
        same_requested_slot = day and requested_time and slot.get("day") == day and slot.get("time") == requested_time
        if not same_requested_slot:
            alternatives.append(sanitize_slot(slot))

    return jsonify(
        {
            "success": True,
            "requested": {
                "doctor": doctor or None,
                "specialty": specialty or None,
                "day": day,
                "time": requested_time,
            },
            "alternate_slots": alternatives[:20],
            "is_available": bool(alternatives),
        }
    ), 200


@app.get("/get-faq")
def get_faq():
    faq = {
        "hospital": "Sumitra Hospital OPD appointment assistant.",
        "appointment": "Appointments can be booked by sharing patient name, 10-digit phone number, doctor or specialty, day, and time.",
        "cancellation": "Appointments can be cancelled using the appointment ID or registered 10-digit phone number.",
        "rescheduling": "Appointments can be rescheduled only when the requested new doctor slot is available.",
        "emergency": "For medical emergencies, please call the local emergency helpline or visit the emergency department immediately.",
        "location": "Please contact Sumitra Hospital reception for current address and directions.",
        "working_hours": "OPD schedules vary by doctor. Some specialists are available only on prior appointment.",
        "data_source": SOURCE_NAME,
    }
    return jsonify({"success": True, "faq": faq}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
