# Sumitra Hospital Voice AI Appointment Backend

This project is a small but practical backend for a hospital appointment booking voice assistant. The idea is simple: a caller can speak to a Vapi assistant, ask for a doctor or department, check OPD availability, and book, cancel, or reschedule an appointment.

The backend is built with Flask and uses Firebase Firestore for storing doctors and appointment slots. Instead of using random demo data, the seed data is based on the publicly available Sumitra Hospital OPD timetable used for this assignment.

Current deployed backend:

```text
https://voice-agent-ai-3omf.onrender.com
```

## Features

- Stores doctors and booked appointments in Firebase Firestore
- Seeds real OPD schedule data from the Sumitra Hospital timetable
- Works with Vapi tool calls using simple JSON input and output
- Checks doctor availability by day and specialty
- Books appointments only after checking for double-booking conflicts
- Cancels appointments using a short human-friendly booking ID
- Reschedules appointments only when the new slot is actually free
- Suggests alternate slots when the requested slot is unavailable
- Protects the seed endpoint with `SEED_SECRET_KEY`
- Falls back to `appointments.json` locally if Firebase credentials are not configured
- Runs on Render with `gunicorn`

## Firestore Structure

### Collection: `doctors`

Each document represents one doctor schedule entry.

```json
{
  "name": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "days": ["Monday", "Wednesday", "Friday"],
  "startTime": "5:00 PM",
  "endTime": "6:00 PM",
  "availabilityType": "Scheduled",
  "source": "Sumitra Hospital OPD timetable"
}
```

Doctors with "On Prior Appointment" availability are stored in `doctors`, but regular bookable slots are not generated for them.

### Collection: `appointments`

Appointment documents are created only when a patient books a slot. The seed endpoint does not pre-create appointment slots, which keeps deployment lightweight on Render's free tier.

```json
{
  "doctor": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "day": "Monday",
  "time": "5:00 PM",
  "patient_name": "Pratik Raj",
  "phone": "9876543210",
  "reason": "General consultation",
  "status": "Booked",
  "booking_id": "APT-7K3P",
  "booked_at": "2026-06-17T10:30:00Z",
  "cancelled_at": "",
  "rescheduled_at": "",
  "source": "Sumitra Hospital OPD timetable"
}
```

Availability is calculated from the `doctors` schedule and active booked appointments.

## OPD Timetable Source

The doctor schedule used in this project is based on the Sumitra Hospital OPD timetable that was provided for the assignment and is treated as publicly available hospital schedule information. No private patient data is used in the seed data.

To make the data source clear inside Firestore, every seeded doctor and appointment slot stores this label:

```text
Sumitra Hospital OPD timetable
```

Doctors included in the seed data:

- Dr. Rajesh Goel, Nephrology, Sunday, 11:00 AM to 12:00 PM
- Dr. Somya Agarwal, Gastroenterology, Monday to Friday, 10:00 AM to 12:00 PM
- Dr. Ayushi Agarwal, Cardiology, Monday, Wednesday, Friday, 5:00 PM to 6:00 PM
- Dr. Vikas Bansal, Urology, Monday, Wednesday, Friday, 5:00 PM to 6:00 PM
- Dr. Rekha Mittal, Paediatric Neurology, Monday, Friday, 3:00 PM to 4:00 PM
- Dr. Shazia Zaidi, Dermatology & Venereology, Tuesday, Thursday, Saturday, 12:00 PM to 1:00 PM
- Dr. Neha Saini, Dental, Monday to Saturday, 10:00 AM to 6:00 PM
- Dr. Jyoti Bhatia, Physiotherapy, Monday to Saturday, 10:00 AM to 5:00 PM
- Dr. Nitin Kumar Rai, Neurology, Monday to Saturday, 9:00 AM to 10:00 AM
- Dr. Alok Sharma, Ophthalmology, Monday, Wednesday, Friday, Saturday, 10:00 AM to 12:00 PM
- Dr. Alok Sharma, Ophthalmology, Tuesday, Thursday, 2:00 PM to 4:00 PM
- Dr. Kalpana Upamanyu, Psychology, Monday, Wednesday, Friday, 12:00 PM to 2:00 PM
- Dr. A. K. Arora, Respiratory Medicine, On Prior Appointment
- Dr. Naman Utreja, Oncology, On Prior Appointment
- Dr. Ashwani Mishra, Paediatrics Surgery, Monday, Thursday, 6:00 PM to 7:00 PM
- Dr. Hemant Kumar, Neuro Surgery, On Prior Appointment

## Environment Variables

Required for production:

```text
FIREBASE_CREDENTIALS_JSON
SEED_SECRET_KEY
```

Optional:

```text
PORT
FLASK_DEBUG
LOG_LEVEL
```

### Where To Put Firebase Credentials

Do not commit the Firebase service account JSON file to GitHub.

For Render, open your Web Service and go to:

```text
Environment -> Add Environment Variable
```

Add:

```text
Key: FIREBASE_CREDENTIALS_JSON
Value: paste the full Firebase service account JSON content
```

Also add:

```text
Key: SEED_SECRET_KEY
Value: choose a long private random string
```

For local PowerShell testing:

```powershell
$env:FIREBASE_CREDENTIALS_JSON = Get-Content -Raw "C:\Users\Lenovo\Downloads\voice-ai-agent-81fca-firebase-adminsdk-fbsvc-4a6468aa9a.json"
$env:SEED_SECRET_KEY = "your-local-seed-secret"
```

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

```bash
python app.py
```

Local base URL:

```text
http://localhost:5000
```

If `FIREBASE_CREDENTIALS_JSON` is missing, the app still runs by using `appointments.json` as a local fallback. This is useful while testing the Flask routes before connecting Firebase.

## API Endpoints

All endpoints return JSON and include a `success` boolean.

### GET `/health`

```bash
curl http://localhost:5000/health
```

### POST `/seed-data`

Seeds the real Sumitra Hospital OPD timetable into the `doctors` collection. It does not create appointment slot documents.

```bash
curl -X POST http://localhost:5000/seed-data ^
  -H "Content-Type: application/json" ^
  -H "X-Seed-Key: your-local-seed-secret" ^
  -d "{}"
```

### POST `/check-availability`

Specialty is optional.

```bash
curl -X POST http://localhost:5000/check-availability ^
  -H "Content-Type: application/json" ^
  -d "{\"day\":\"Monday\",\"specialty\":\"Cardiology\"}"
```

Request:

```json
{
  "day": "Monday",
  "specialty": "Cardiology"
}
```

### POST `/book-appointment`

```bash
curl -X POST http://localhost:5000/book-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Pratik Raj\",\"phone\":\"9876543210\",\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\",\"reason\":\"General consultation\"}"
```

Request:

```json
{
  "name": "Pratik Raj",
  "phone": "9876543210",
  "doctor": "Dr. Ayushi Agarwal",
  "specialty": "Cardiology",
  "day": "Monday",
  "time": "5:00 PM",
  "reason": "General consultation"
}
```

If the same doctor/day/time is already booked, the endpoint returns `409`.

The response includes a short `booking_id`, for example `APT-7K3P`. This is the only ID the voice assistant should read to the caller.

### POST `/cancel-appointment`

Cancel by booking ID:

```bash
curl -X POST http://localhost:5000/cancel-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"booking_id\":\"APT-7K3P\"}"
```

Request:

```json
{
  "booking_id": "APT-7K3P"
}
```

Phone plus appointment details are still supported as a fallback:

```json
{
  "phone": "9876543210",
  "doctor": "Dr. Somya Agarwal",
  "day": "Tuesday",
  "time": "11:00 AM"
}
```

If the appointment is not found, the API returns `404`.

### POST `/reschedule-appointment`

```bash
curl -X POST http://localhost:5000/reschedule-appointment ^
  -H "Content-Type: application/json" ^
  -d "{\"booking_id\":\"APT-7K3P\",\"new_day\":\"Wednesday\",\"new_time\":\"10:00 AM\"}"
```

Request:

```json
{
  "booking_id": "APT-7K3P",
  "new_day": "Wednesday",
  "new_time": "10:00 AM"
}
```

Phone plus old appointment details are still supported as a fallback.

The API checks the new slot before rescheduling. If the new slot is already booked, it returns `409`.

### POST `/get-alternate-slots`

```bash
curl -X POST http://localhost:5000/get-alternate-slots ^
  -H "Content-Type: application/json" ^
  -d "{\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\"}"
```

### GET `/get-faq`

```bash
curl http://localhost:5000/get-faq
```

## Vapi Integration Guide

In Vapi, create tools that call these backend URLs. The assistant should collect the required details from the caller, then pass them to the matching endpoint.

```text
GET  https://voice-agent-ai-3omf.onrender.com/health
POST https://voice-agent-ai-3omf.onrender.com/check-availability
POST https://voice-agent-ai-3omf.onrender.com/book-appointment
POST https://voice-agent-ai-3omf.onrender.com/cancel-appointment
POST https://voice-agent-ai-3omf.onrender.com/reschedule-appointment
POST https://voice-agent-ai-3omf.onrender.com/get-alternate-slots
GET  https://voice-agent-ai-3omf.onrender.com/get-faq
```

### Vapi Tool Setup

Use these tool names in Vapi so the assistant prompt stays readable.

#### `checkAvailability`

URL:

```text
POST https://voice-agent-ai-3omf.onrender.com/check-availability
```

Request body properties:

- `day` string, required, example `Monday`
- `specialty` string, optional, example `Cardiology`

Response body properties:

- `success` boolean
- `day` string
- `specialty` string or null
- `available_slots` array
- `is_available` boolean
- `prior_appointment_doctors` array

#### `bookAppointment`

URL:

```text
POST https://voice-agent-ai-3omf.onrender.com/book-appointment
```

Request body properties:

- `name` string, required
- `phone` string, required, 10 digits
- `doctor` string, required
- `specialty` string, required
- `day` string, required
- `time` string, required
- `reason` string, optional

Response body properties:

- `success` boolean
- `message` string
- `booking_id` string, example `APT-7K3P`
- `doctor` string
- `specialty` string
- `day` string
- `time` string

#### `cancelAppointment`

URL:

```text
POST https://voice-agent-ai-3omf.onrender.com/cancel-appointment
```

Request body properties:

- `booking_id` string, required for the recommended flow
- `phone` string, optional fallback
- `doctor` string, optional fallback
- `day` string, optional fallback
- `time` string, optional fallback

Recommended Vapi request body:

```json
{
  "booking_id": "APT-7K3P"
}
```

Response body properties:

- `success` boolean
- `message` string
- `booking_id` string
- `doctor` string
- `specialty` string
- `day` string
- `time` string
- `status` string

#### `rescheduleAppointment`

URL:

```text
POST https://voice-agent-ai-3omf.onrender.com/reschedule-appointment
```

Request body properties:

- `booking_id` string, required for the recommended flow
- `new_day` string, required
- `new_time` string, required
- `phone` string, optional fallback
- `doctor` string, optional fallback
- `old_day` string, optional fallback
- `old_time` string, optional fallback
- `new_doctor` string, optional
- `new_specialty` string, optional

Recommended Vapi request body:

```json
{
  "booking_id": "APT-7K3P",
  "new_day": "Wednesday",
  "new_time": "10:00 AM"
}
```

Response body properties:

- `success` boolean
- `message` string
- `booking_id` string
- `doctor` string
- `specialty` string
- `day` string
- `time` string
- `status` string

Important Vapi prompt rule: the assistant should read only the `booking_id` to the caller. It should never read raw Firestore document IDs.

The backend supports plain JSON request bodies and common Vapi `arguments` payloads, so it can work both from curl/Postman and from the voice assistant.

## Render Deployment

1. Push this project to GitHub.
2. Open Render and create or update the Web Service.
3. Set the build command:

```bash
pip install -r requirements.txt
```

4. Set the start command:

```bash
gunicorn app:app
```

5. Add environment variables:

```text
FIREBASE_CREDENTIALS_JSON=<paste full service account JSON>
SEED_SECRET_KEY=<your private seed key>
```

6. Deploy.
7. Run `/seed-data` once after deployment to insert the Sumitra Hospital OPD timetable into the `doctors` collection.

Render seed command example:

```bash
curl -X POST https://voice-agent-ai-3omf.onrender.com/seed-data \
  -H "Content-Type: application/json" \
  -H "X-Seed-Key: YOUR_SEED_SECRET_KEY" \
  -d "{}"
```

## Testing Checklist

```bash
python -m py_compile app.py
```

Health:

```bash
curl http://localhost:5000/health
```

Seed:

```bash
curl -X POST http://localhost:5000/seed-data -H "X-Seed-Key: your-local-seed-secret" -H "Content-Type: application/json" -d "{}"
```

Check Monday Cardiology availability:

```bash
curl -X POST http://localhost:5000/check-availability -H "Content-Type: application/json" -d "{\"day\":\"Monday\",\"specialty\":\"Cardiology\"}"
```

Book Dr. Ayushi Agarwal:

```bash
curl -X POST http://localhost:5000/book-appointment -H "Content-Type: application/json" -d "{\"name\":\"Pratik Raj\",\"phone\":\"9876543210\",\"doctor\":\"Dr. Ayushi Agarwal\",\"specialty\":\"Cardiology\",\"day\":\"Monday\",\"time\":\"5:00 PM\",\"reason\":\"General consultation\"}"
```

Run the same booking command again. It should return:

```text
409 Conflict
```

## Limitations

- The timetable is weekday-based, so it does not yet handle calendar dates, holidays, or doctor leave.
- Availability uses one-hour blocks from the OPD timing range.
- Doctors marked "On Prior Appointment" are saved in Firestore, but automatic slots are not created for them.
- The timetable data is used as publicly available schedule information for this assignment/demo. It should be verified with the hospital before real-world use.
- `appointments.json` is only for local fallback. Firestore is the intended production database.
- Before using this in a real hospital workflow, add authentication, admin controls, audit logs, date-wise scheduling, and stronger data privacy controls.
