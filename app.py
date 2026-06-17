import json
import os
import re
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request


load_dotenv()

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "appointments.json")

VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PHONE_PATTERN = re.compile(r"^\d{10}$")


def normalize_day(day):
    """दिन को सही format में बदलता है, जैसे monday -> Monday."""
    if not isinstance(day, str):
        return None

    day = day.strip().lower()
    for valid_day in VALID_DAYS:
        if day == valid_day.lower():
            return valid_day
    return None


def parse_time(time_text):
    """समय को validate करके datetime time object में बदलता है."""
    if not isinstance(time_text, str):
        return None

    cleaned_time = time_text.strip().upper()
    accepted_formats = ["%I:%M %p", "%I %p"]

    for time_format in accepted_formats:
        try:
            return datetime.strptime(cleaned_time, time_format).time()
        except ValueError:
            continue

    return None


def is_valid_clinic_time(time_text):
    """Clinic timing 9:00 AM से 6:00 PM तक है."""
    parsed_time = parse_time(time_text)
    if parsed_time is None:
        return False

    start_time = datetime.strptime("9:00 AM", "%I:%M %p").time()
    end_time = datetime.strptime("6:00 PM", "%I:%M %p").time()
    return start_time <= parsed_time <= end_time


def format_time(time_text):
    """समय को एक standard format में save करता है."""
    parsed_time = parse_time(time_text)
    if parsed_time is None:
        return None

    formatted = datetime.strptime(parsed_time.strftime("%H:%M"), "%H:%M").strftime("%I:%M %p")
    return formatted.lstrip("0")


def is_valid_phone(phone):
    """Phone number exactly 10 digits होना चाहिए."""
    return isinstance(phone, str) and PHONE_PATTERN.match(phone.strip()) is not None


def load_database():
    """appointments.json से data load करता है."""
    if not os.path.exists(DB_FILE):
        return {"available_slots": {}, "booked_appointments": []}

    with open(DB_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_database(data):
    """Updated appointment data को appointments.json में save करता है."""
    with open(DB_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def json_error(message, status_code=400, details=None):
    """हर error response JSON format में देता है."""
    response = {"success": False, "error": message}
    if details:
        response["details"] = details
    return jsonify(response), status_code


def parse_tool_arguments(arguments):
    """Vapi arguments kabhi dict aur kabhi JSON string ke roop me aa sakte hain."""
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            parsed_arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return parsed_arguments if isinstance(parsed_arguments, dict) else {}

    return {}


def get_request_data():
    """Vapi या normal API request से JSON body निकालता है."""
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


def validate_day_time_phone(data, require_time=True, require_phone=True):
    """Common validation helper ताकि सभी endpoints consistent रहें."""
    day = normalize_day(data.get("day"))
    if not day:
        return None, None, None, json_error("Invalid day. Please choose Monday to Friday.", 400)

    appointment_time = None
    if require_time:
        appointment_time = format_time(data.get("time"))
        if not appointment_time or not is_valid_clinic_time(appointment_time):
            return None, None, None, json_error("Invalid time. Please choose a time between 9:00 AM and 6:00 PM.", 400)

    phone = None
    if require_phone:
        phone = str(data.get("phone", "")).strip()
        if not is_valid_phone(phone):
            return None, None, None, json_error("Invalid phone. Phone number must be exactly 10 digits.", 400)

    return day, appointment_time, phone, None


def find_booked_appointments(data, phone):
    """Phone number से active appointments ढूंढता है."""
    return [
        appointment
        for appointment in data.get("booked_appointments", [])
        if appointment.get("phone") == phone and appointment.get("status") == "booked"
    ]


@app.errorhandler(404)
def not_found(_error):
    return json_error("Endpoint not found.", 404)


@app.errorhandler(405)
def method_not_allowed(_error):
    return json_error("Method not allowed for this endpoint.", 405)


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unexpected server error: %s", error)
    return json_error("Internal server error.", 500)


@app.get("/health")
def health_check():
    return jsonify({"status": "ok"}), 200


@app.post("/check-availability")
def check_availability():
    # Voice bot caller ka preferred day/time check karta hai, booking nahi banata.
    data = get_request_data()
    day = normalize_day(data.get("day"))

    if not day:
        return json_error("Invalid day. Please choose Monday to Friday.", 400)

    requested_time = data.get("time")
    formatted_time = None
    if requested_time:
        formatted_time = format_time(requested_time)
        if not formatted_time or not is_valid_clinic_time(formatted_time):
            return json_error("Invalid time. Please choose a time between 9:00 AM and 6:00 PM.", 400)

    database = load_database()
    available_slots = database.get("available_slots", {}).get(day, [])
    is_available = formatted_time in available_slots if formatted_time else bool(available_slots)

    return jsonify(
        {
            "success": True,
            "day": day,
            "requested_time": formatted_time,
            "is_available": is_available,
            "available_slots": available_slots,
        }
    ), 200


@app.post("/book-appointment")
def book_appointment():
    # Slot book hone ke baad us time ko available_slots se hata dete hain.
    data = get_request_data()
    day, appointment_time, phone, validation_error = validate_day_time_phone(data)
    if validation_error:
        return validation_error

    database = load_database()
    available_slots = database.setdefault("available_slots", {}).setdefault(day, [])

    if appointment_time not in available_slots:
        return json_error("Requested slot is not available.", 409, {"available_slots": available_slots})

    existing_appointments = find_booked_appointments(database, phone)
    if existing_appointments:
        return json_error("This phone number already has a booked appointment.", 409, {"appointments": existing_appointments})

    appointment = {
        "appointment_id": f"APT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
        "name": str(data.get("name", "Patient")).strip() or "Patient",
        "phone": phone,
        "day": day,
        "time": appointment_time,
        "reason": str(data.get("reason", "General consultation")).strip() or "General consultation",
        "status": "booked",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    available_slots.remove(appointment_time)
    database.setdefault("booked_appointments", []).append(appointment)
    save_database(database)

    return jsonify({"success": True, "message": "Appointment booked successfully.", "appointment": appointment}), 201


@app.post("/cancel-appointment")
def cancel_appointment():
    # Cancelled appointment ka slot wapas available_slots me add hota hai.
    data = get_request_data()
    phone = str(data.get("phone", "")).strip()

    if not is_valid_phone(phone):
        return json_error("Invalid phone. Phone number must be exactly 10 digits.", 400)

    database = load_database()
    matching_appointments = find_booked_appointments(database, phone)

    if not matching_appointments:
        return json_error("No active appointment found for this phone number.", 404)

    cancelled_appointments = []
    for appointment in matching_appointments:
        appointment["status"] = "cancelled"
        appointment["cancelled_at"] = datetime.utcnow().isoformat() + "Z"
        database.setdefault("available_slots", {}).setdefault(appointment["day"], []).append(appointment["time"])
        database["available_slots"][appointment["day"]] = sorted(
            set(database["available_slots"][appointment["day"]]),
            key=lambda item: parse_time(item),
        )
        cancelled_appointments.append(appointment)

    save_database(database)

    return jsonify(
        {
            "success": True,
            "message": "Appointment cancelled successfully.",
            "cancelled_appointments": cancelled_appointments,
        }
    ), 200


@app.post("/reschedule-appointment")
def reschedule_appointment():
    # Reschedule me old slot release hota hai aur new slot reserve hota hai.
    data = get_request_data()
    phone = str(data.get("phone", "")).strip()
    new_day = normalize_day(data.get("new_day") or data.get("day"))
    new_time = format_time(data.get("new_time") or data.get("time"))

    if not is_valid_phone(phone):
        return json_error("Invalid phone. Phone number must be exactly 10 digits.", 400)
    if not new_day:
        return json_error("Invalid day. Please choose Monday to Friday.", 400)
    if not new_time or not is_valid_clinic_time(new_time):
        return json_error("Invalid time. Please choose a time between 9:00 AM and 6:00 PM.", 400)

    database = load_database()
    matching_appointments = find_booked_appointments(database, phone)

    if not matching_appointments:
        return json_error("No active appointment found for this phone number.", 404)

    available_slots = database.setdefault("available_slots", {}).setdefault(new_day, [])
    if new_time not in available_slots:
        return json_error("Requested new slot is not available.", 409, {"available_slots": available_slots})

    appointment = matching_appointments[0]
    old_day = appointment["day"]
    old_time = appointment["time"]

    database.setdefault("available_slots", {}).setdefault(old_day, []).append(old_time)
    database["available_slots"][old_day] = sorted(set(database["available_slots"][old_day]), key=lambda item: parse_time(item))
    database["available_slots"][new_day].remove(new_time)

    appointment["day"] = new_day
    appointment["time"] = new_time
    appointment["rescheduled_at"] = datetime.utcnow().isoformat() + "Z"

    save_database(database)

    return jsonify(
        {
            "success": True,
            "message": "Appointment rescheduled successfully.",
            "old_slot": {"day": old_day, "time": old_time},
            "new_slot": {"day": new_day, "time": new_time},
            "appointment": appointment,
        }
    ), 200


@app.get("/get-faq")
def get_faq():
    faq = {
        "clinic_hours": "The clinic is open Monday to Friday from 9:00 AM to 6:00 PM.",
        "booking": "Appointments can be booked by providing name, phone number, day, and preferred time.",
        "cancellation": "Appointments can be cancelled using the registered 10-digit phone number.",
        "rescheduling": "Appointments can be rescheduled using the registered phone number and a new available slot.",
        "emergency": "For medical emergencies, please call your local emergency helpline immediately.",
        "location": "Please contact the clinic reception for the latest address and directions.",
    }
    return jsonify({"success": True, "faq": faq}), 200


@app.post("/get-alternate-slots")
def get_alternate_slots():
    data = get_request_data()
    preferred_day = normalize_day(data.get("day"))

    if not preferred_day:
        return json_error("Invalid day. Please choose Monday to Friday.", 400)

    database = load_database()
    available_slots = database.get("available_slots", {})
    alternate_slots = {
        day: slots
        for day, slots in available_slots.items()
        if day != preferred_day and day in VALID_DAYS and slots
    }

    return jsonify(
        {
            "success": True,
            "preferred_day": preferred_day,
            "alternate_slots": alternate_slots,
        }
    ), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
