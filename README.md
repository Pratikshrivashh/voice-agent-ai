# Voice AI Hospital Receptionist

A phone-based hospital receptionist that uses Vapi and a Flask API to check schedules and manage appointments.

---

## Why I Built This

Hospital reception desks spend a lot of time answering the same calls: Which doctor is available? Can I book Tuesday morning? Can I move my appointment?

When the desk is busy, calls get missed and patients have to try again. The receptionist also has to switch between talking to patients, checking schedules, and recording appointment details.

Voice is useful here because a patient can call and explain what they need in normal language. The assistant handles the routine parts of scheduling while the reception team can focus on patients who need a person.

This is a working assignment project, not an official hospital booking service.

---

## How It Works

```text
Patient calls the clinic number
              |
              v
Vapi voice assistant answers
              |
              v
Patient speaks naturally
              |
              v
Flask backend checks availability
              |
              v
Appointment is stored in Firestore
              |
              v
Booking ID is returned to the patient
```

Vapi handles the phone conversation. It calls this API when it needs schedule or appointment data. The backend validates the request, reads or writes Firestore, and sends a small JSON response that the assistant can read back to the caller.

---

## What Currently Works

- [x] Check doctor availability
- [x] Book appointments
- [x] Cancel appointments
- [x] Reschedule appointments
- [x] Generate human-friendly booking IDs
- [x] Basic FAQ handling

---

## Tech Stack

- **Python**: keeps the backend small and easy to inspect.
- **Flask**: provides the HTTP endpoints used by Vapi.
- **Vapi**: handles the voice assistant, phone call, and tool calls.
- **Firestore**: stores doctors, schedules, and booked appointments in production.
- **JSON storage**: lets the API run locally when Firebase credentials are not configured.
- **Render**: runs the Flask API with Gunicorn.

---

## Running Locally

Clone the repository and install the Python packages:

```bash
git clone https://github.com/Pratikshrivashh/voice-agent-ai.git
cd voice-agent-ai
pip install -r requirements.txt
```

Start the Flask server:

```bash
python app.py
```

Check that it is running:

```bash
curl http://localhost:5000/health
```

Without Firebase credentials, the app uses `appointments.json`. To use Firestore locally, create a `.env` file:

```env
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project-id"}
SEED_SECRET_KEY=choose-a-long-random-value
LOG_LEVEL=INFO
```

`FIREBASE_CREDENTIALS_JSON` must contain the full service account JSON as one environment variable. Do not commit the service account file or its contents.

Seed the doctor timetable after the server starts:

```bash
curl -X POST http://localhost:5000/seed-data \
  -H "Content-Type: application/json" \
  -H "X-Seed-Key: choose-a-long-random-value" \
  -d '{}'
```

---

## API Quick Reference

Local examples use `http://localhost:5000`. Replace it with `https://voice-agent-ai-3omf.onrender.com` when testing the deployed API.

### Health Check

**Method:** `GET`

**URL:** `/health`

**Purpose:** Confirms that the API is running and reports which database is active.

```bash
curl http://localhost:5000/health
```

```json
{
  "success": true,
  "status": "ok",
  "database": "Firestore",
  "firebase_configured": true,
  "firebase_message": "Firebase connected."
}
```

### Seed Doctor Data

**Method:** `POST`

**URL:** `/seed-data`

**Purpose:** Adds the Sumitra Hospital OPD timetable to the configured database. This route is protected by `SEED_SECRET_KEY`.

```bash
curl -X POST http://localhost:5000/seed-data \
  -H "Content-Type: application/json" \
  -H "X-Seed-Key: your-seed-secret" \
  -d '{}'
```

```json
{
  "success": true,
  "message": "Sumitra Hospital OPD timetable seeded successfully.",
  "database": "Firestore",
  "doctor_count": 16,
  "appointment_slot_count": 0,
  "note": "Only doctors were seeded. Appointment documents are created when a user books.",
  "source": "Sumitra Hospital OPD timetable"
}
```

### Check Availability

**Method:** `POST`

**URL:** `/check-availability`

**Purpose:** Returns available slots for a day. `specialty` is optional.

```bash
curl -X POST http://localhost:5000/check-availability \
  -H "Content-Type: application/json" \
  -d '{
    "day": "Tuesday",
    "specialty": "Gastroenterology"
  }'
```

```json
{
  "success": true,
  "day": "Tuesday",
  "specialty": "Gastroenterology",
  "available_slots": [
    {
      "doctor": "Dr. Somya Agarwal",
      "specialty": "Gastroenterology",
      "day": "Tuesday",
      "time": "10:00 AM"
    },
    {
      "doctor": "Dr. Somya Agarwal",
      "specialty": "Gastroenterology",
      "day": "Tuesday",
      "time": "11:00 AM"
    }
  ],
  "prior_appointment_doctors": [],
  "is_available": true
}
```

### Book an Appointment

**Method:** `POST`

**URL:** `/book-appointment`

**Purpose:** Books an available slot and returns a short booking ID. Phone numbers must contain 10 digits.

```bash
curl -X POST http://localhost:5000/book-appointment \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pratik Raj",
    "phone": "9876543210",
    "doctor": "Dr. Somya Agarwal",
    "specialty": "Gastroenterology",
    "day": "Tuesday",
    "time": "11:00 AM",
    "reason": "General consultation"
  }'
```

```json
{
  "success": true,
  "message": "Appointment booked successfully.",
  "booking_id": "APT-CV90",
  "doctor": "Dr. Somya Agarwal",
  "day": "Tuesday",
  "time": "11:00 AM",
  "specialty": "Gastroenterology"
}
```

If the slot is already booked, the API returns HTTP `409`.

### Cancel an Appointment

**Method:** `POST`

**URL:** `/cancel-appointment`

**Purpose:** Cancels an active appointment. The short booking ID is the recommended lookup method.

```bash
curl -X POST http://localhost:5000/cancel-appointment \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "APT-CV90"
  }'
```

```json
{
  "success": true,
  "message": "Appointment cancelled successfully.",
  "booking_id": "APT-CV90",
  "doctor": "Dr. Somya Agarwal",
  "day": "Tuesday",
  "time": "11:00 AM",
  "specialty": "Gastroenterology",
  "status": "Cancelled"
}
```

The route also supports the older lookup format using `phone`, `doctor`, `day`, and `time`.

### Reschedule an Appointment

**Method:** `POST`

**URL:** `/reschedule-appointment`

**Purpose:** Moves an active appointment to an available slot while keeping the same booking ID.

```bash
curl -X POST http://localhost:5000/reschedule-appointment \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "APT-CV90",
    "new_day": "Wednesday",
    "new_time": "10:00 AM"
  }'
```

```json
{
  "success": true,
  "message": "Appointment rescheduled successfully.",
  "booking_id": "APT-CV90",
  "doctor": "Dr. Somya Agarwal",
  "day": "Wednesday",
  "time": "10:00 AM",
  "specialty": "Gastroenterology",
  "status": "Booked"
}
```

If the new slot is already booked, the API returns HTTP `409`.

### Get Alternate Slots

**Method:** `POST`

**URL:** `/get-alternate-slots`

**Purpose:** Suggests other available slots for a doctor or specialty.

```bash
curl -X POST http://localhost:5000/get-alternate-slots \
  -H "Content-Type: application/json" \
  -d '{
    "doctor": "Dr. Ayushi Agarwal",
    "specialty": "Cardiology",
    "day": "Monday",
    "time": "5:00 PM"
  }'
```

```json
{
  "success": true,
  "requested": {
    "doctor": "Dr. Ayushi Agarwal",
    "specialty": "Cardiology",
    "day": "Monday",
    "time": "5:00 PM"
  },
  "alternate_slots": [
    {
      "doctor": "Dr. Ayushi Agarwal",
      "specialty": "Cardiology",
      "day": "Wednesday",
      "time": "5:00 PM"
    }
  ],
  "is_available": true
}
```

### Get FAQs

**Method:** `GET`

**URL:** `/get-faq`

**Purpose:** Returns short answers about booking, cancellation, rescheduling, emergencies, location, and working hours.

```bash
curl http://localhost:5000/get-faq
```

```json
{
  "success": true,
  "faq": {
    "hospital": "Sumitra Hospital OPD appointment assistant.",
    "appointment": "Appointments can be booked by sharing patient name, 10-digit phone number, doctor or specialty, day, and time.",
    "cancellation": "Appointments can be cancelled using the short booking ID shared at booking time.",
    "rescheduling": "Appointments can be rescheduled using the short booking ID, only when the requested new slot is available.",
    "emergency": "For medical emergencies, please call the local emergency helpline or visit the emergency department immediately.",
    "location": "Please contact Sumitra Hospital reception for current address and directions.",
    "working_hours": "OPD schedules vary by doctor. Some specialists are available only on prior appointment.",
    "data_source": "Sumitra Hospital OPD timetable"
  }
}
```

Error responses use the same small JSON shape:

```json
{
  "success": false,
  "message": "Requested slot is already booked."
}
```

The main status codes are `200` for a successful request, `201` for a booking, `400` for invalid input, `404` when a slot or appointment cannot be found, `409` for a booking conflict, and `500` for an unexpected server error.

---

## Using It With Vapi

1. Create an account at [Vapi](https://vapi.ai/).
2. Create an assistant and give it a simple receptionist prompt. Tell it to collect one missing detail at a time and never claim a booking succeeded until the booking tool returns `success: true`.
3. Add HTTP tools for `/check-availability`, `/book-appointment`, `/cancel-appointment`, `/reschedule-appointment`, `/get-alternate-slots`, and `/get-faq`.
4. Set each tool URL to the deployed Render address, for example `https://voice-agent-ai-3omf.onrender.com/book-appointment`.
5. Match each tool's JSON body to the request examples above. Make `booking_id` the normal field for cancellation and rescheduling.
6. Buy a Vapi phone number or connect a supported number you already own.
7. Attach the number to the assistant and call it.

Keep the tool descriptions direct. For example, the booking tool should say that it books only after the patient confirms the doctor, day, time, name, and phone number. The assistant should read the returned `booking_id` aloud and should never read a Firestore document ID.

---

## Deployment

The backend is designed to run as a Render web service.

1. Push the repository to GitHub.
2. Sign in to [Render](https://render.com/) and open the dashboard.
3. Select **New**, then **Web Service**.
4. Connect your GitHub account and choose the `voice-agent-ai` repository.
5. Use these settings:

```text
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

6. Open the service's **Environment** tab and add:

```text
FIREBASE_CREDENTIALS_JSON = the full Firebase service account JSON
SEED_SECRET_KEY = a long random value
LOG_LEVEL = INFO
```

7. Click **Create Web Service** or **Deploy Latest Commit**.
8. Wait for the deploy log to show that Gunicorn is listening.
9. Test the public endpoint:

```bash
curl https://voice-agent-ai-3omf.onrender.com/health
```

10. Seed the doctors once:

```bash
curl -X POST https://voice-agent-ai-3omf.onrender.com/seed-data \
  -H "Content-Type: application/json" \
  -H "X-Seed-Key: your-seed-secret" \
  -d '{}'
```

Do not put `FIREBASE_CREDENTIALS_JSON` in GitHub, frontend code, Vercel variables, or any public file. It belongs only in the Render environment for the backend.

---

## Roadmap

- SMS booking confirmations
- Email reminders
- Support for more than one clinic
- A small admin dashboard for reception staff
- Better FAQ retrieval from clinic documents

These are ideas for later work and are not part of the current version.

---

## Known Issues

- FAQ answers are basic strings, not answers retrieved from hospital documents.
- There is no staff or patient authentication.
- Appointment validation follows the seeded timetable but does not understand holidays, doctor leave, or temporary schedule changes.
- There is no payment flow.
- The quality of the phone conversation depends heavily on the Vapi prompt, model, voice, and tool configuration.
- Render's free service can sleep when unused, so the first call may take longer.
- The JSON fallback is useful for local testing but is not suitable for multiple production workers.
- This demo does not create official hospital appointments and should not receive sensitive medical information.

---

## Contributing

Fork the repository, create a branch, and open a pull request with a clear description of the change. Bug fixes, validation improvements, tests, and cleaner Vapi prompts are all useful contributions.

---

## Final Note

This project was built as part of the 2Care.ai Voice AI assignment. The goal was not to build a perfect product, but to build something real that can answer a phone call and manage appointments.
