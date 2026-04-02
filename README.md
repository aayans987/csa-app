# CSA — Co-op Support Application
## Setup Instructions (takes 2 minutes)

### Step 1 — Install dependencies
Open a terminal in this folder and run:
```
pip install flask flask-cors
```

### Step 2 — Run the app
```
python app.py
```

### Step 3 — Open in browser
Go to: http://localhost:5000

---

## Demo Credentials
- **Coordinator:** coordinator / admin123
- **Student login:** 501100001 / pass123
- **Student login:** 501100003 / pass123

## Features
- Student application form (with validation)
- Coordinator dashboard (accept/reject applicants, provisional + final decisions)
- Student login + work term report submission
- Supervisor registration + evaluation form (star ratings) + PDF upload
- Reporting: missing reports, evaluation status, rejection tracking
- Email reminder simulation
- All data persists in SQLite database (csa.db)
