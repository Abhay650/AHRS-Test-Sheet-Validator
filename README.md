# AHRS Test Sheet – Web Application

A Python-based web application that automates AHRS test sheet processing by extracting test parameters and 2×RMSE values from uploaded TXT files, calculating results, and generating downloadable test sheets.

## Features

- Upload and process multiple TXT files.
- Automatically detect test type, preparation type, and angle.
- Extract 2×RMSE values using Regular Expressions.
- Calculate test results against predefined engineering limits.
- Display OK, NOT OK, and N/A statuses.
- Export processed test sheet data as a TXT file.

## Tech Stack

- **Language:** Python
- **Backend:** FastAPI
- **Data Validation:** Pydantic
- **Processing:** Regex
- **Deployment:** Vercel

## Project Structure

```text
sbkv-web/
│
├── api/
│   └── index.py          # FastAPI backend and processing logic
│
├── public/               # Public application assets
│
├── requirements.txt      # Python dependencies
│
└── vercel.json           # Vercel deployment configuration
```

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/Abhay650/sbkv-web.git
```

### Navigate to Project

```bash
cd sbkv-web
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
uvicorn api.index:app --reload
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/rows` | Retrieve test sheet structure |
| POST | `/api/process` | Process uploaded TXT files |
| POST | `/api/compute` | Calculate test results |
| POST | `/api/export` | Generate downloadable test sheet |

## Key Learning Outcomes

- Python backend development using FastAPI.
- File handling and text processing.
- Regular Expressions for extracting engineering parameters.
- API development and JSON data handling.
- Automated result calculation and report generation.
- Deployment using Vercel.

## Live Demo

**[Open AHRS Test Sheet Application](https://sbkv-web.vercel.app/)**

## GitHub Repository

**[View Source Code](https://github.com/Abhay650/sbkv-web)**

---

**Developed by Abhay Gupta**  
