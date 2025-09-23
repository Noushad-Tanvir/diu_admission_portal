from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import pandas as pd
import logging
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import re
import difflib
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO, filename="app.log")
logger = logging.getLogger(__name__)

app = FastAPI(title="DIU Admission API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


# SQLite Database Setup with Migration
def init_db():
    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()

    # Create programs table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY,
            name TEXT,
            code TEXT UNIQUE,
            department_code TEXT,
            total_cost REAL,
            credits INTEGER,
            duration REAL,
            description TEXT,
            eligibility TEXT,
            career_prospects TEXT,
            admission_deadline TEXT,
            program_type TEXT,
            accreditation TEXT
        )
    """)

    # Migrate programs table to add missing columns
    existing_columns = [
        info[1] for info in c.execute("PRAGMA table_info(programs)").fetchall()
    ]
    required_columns = {
        "department_code": "TEXT",
        "eligibility": "TEXT",
        "career_prospects": "TEXT",
        "admission_deadline": "TEXT",
        "program_type": "TEXT",
        "accreditation": "TEXT",
    }
    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            c.execute(f"ALTER TABLE programs ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added column {col_name} to programs table")

    # Create other tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS waivers (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            description TEXT,
            waiver_rate TEXT,
            eligibility_criteria TEXT,
            required_documents TEXT,
            deadline TEXT,
            applicable_programs TEXT,
            sgpa_required REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            email TEXT,
            phone TEXT,
            dob TEXT,
            father_name TEXT,
            mother_name TEXT,
            nid TEXT,
            gender TEXT,
            program_code TEXT,
            ssc_gpa REAL,
            hsc_gpa REAL,
            ssc_year INTEGER,
            hsc_year INTEGER,
            ssc_board TEXT,
            hsc_board TEXT,
            ssc_group TEXT,
            hsc_group TEXT,
            family_income REAL,
            is_freedom_fighter_child BOOLEAN,
            is_diu_employee_relative BOOLEAN,
            has_sports_achievement BOOLEAN,
            has_diploma BOOLEAN,
            is_international_student BOOLEAN,
            group_admission BOOLEAN,
            documents_submitted TEXT,
            application_status TEXT,
            submitted_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id TEXT PRIMARY KEY,
            question TEXT,
            answer TEXT,
            keywords TEXT,
            category TEXT,
            source_link TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT,
            code TEXT UNIQUE,
            contact TEXT,
            head TEXT,
            description TEXT,
            programs TEXT,
            faculty TEXT,
            location TEXT,
            website TEXT,
            established_year INTEGER,
            student_capacity INTEGER,
            accreditation TEXT
        )
    """)
    conn.commit()
    conn.close()


# Initialize database
init_db()


# Seed Data with Error Handling
def seed_data():
    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()

    # Programs
    try:
        with open("data/programs.json") as f:
            programs = json.load(f)
        for p in programs:
            try:
                # Validate data types
                total_cost = (
                    float(p["total_cost"]) if p.get("total_cost") is not None else 0.0
                )
                credits = int(p["credits"]) if p.get("credits") is not None else 0
                duration = (
                    float(p["duration"]) if p.get("duration") is not None else 0.0
                )
                eligibility = json.dumps(p.get("eligibility", []))
                career_prospects = json.dumps(p.get("career_prospects", []))

                c.execute(
                    """
                    INSERT OR IGNORE INTO programs (
                        id, name, code, department_code, total_cost, credits, duration, description,
                        eligibility, career_prospects, admission_deadline, program_type, accreditation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        p["id"],
                        p["name"],
                        p["code"],
                        p.get("department_code", ""),
                        total_cost,
                        credits,
                        duration,
                        p.get("description", ""),
                        eligibility,
                        career_prospects,
                        p.get("admission_deadline", ""),
                        p.get("program_type", ""),
                        p.get("accreditation", ""),
                    ),
                )
            except Exception as e:
                logger.error(
                    f"Error inserting program {p.get('code', 'unknown')}: {str(e)}"
                )
                continue
    except Exception as e:
        logger.error(f"Error loading programs.json: {str(e)}")

    # Waivers
    try:
        with open("data/waivers.json") as f:
            waivers = json.load(f)
        c.executemany(
            """
            INSERT OR IGNORE INTO waivers (
                id, name, category, description, waiver_rate, eligibility_criteria,
                required_documents, deadline, applicable_programs, sgpa_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    w["id"],
                    w["name"],
                    w["category"],
                    w["description"],
                    w["waiver_rate"],
                    json.dumps(w["eligibility_criteria"]),
                    json.dumps(w["required_documents"]),
                    w["deadline"],
                    json.dumps(w["applicable_programs"]),
                    w["sgpa_required"],
                )
                for w in waivers
            ],
        )
    except Exception as e:
        logger.error(f"Error loading waivers.json: {str(e)}")

    # FAQs
    try:
        faq_df = pd.read_csv("data/faq.csv")
        faqs = [
            {
                "id": row["Question ID"],
                "question": row["question"],
                "answer": row["answer"],
                "keywords": row.get("keywords", ""),
                "category": row.get("category", "General"),
                "source_link": row.get("Source link", ""),
            }
            for _, row in faq_df.iterrows()
        ]
        c.executemany(
            """
            INSERT OR IGNORE INTO faqs (id, question, answer, keywords, category, source_link)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    f["id"],
                    f["question"],
                    f["answer"],
                    f["keywords"],
                    f["category"],
                    f["source_link"],
                )
                for f in faqs
            ],
        )
    except Exception as e:
        logger.error(f"Error loading faq.csv: {str(e)}")

    # Departments
    try:
        with open("data/departments.json") as f:
            departments = json.load(f)
        c.executemany(
            """
            INSERT OR IGNORE INTO departments (
                id, name, code, contact, head, description, programs, faculty, location,
                website, established_year, student_capacity, accreditation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    d["id"],
                    d["name"],
                    d["code"],
                    d["contact"],
                    d["head"],
                    d["description"],
                    json.dumps(d["programs"]),
                    d["faculty"],
                    d["location"],
                    d["website"],
                    d["established_year"],
                    d["student_capacity"],
                    d["accreditation"],
                )
                for d in departments
            ],
        )
    except Exception as e:
        logger.error(f"Error loading departments.json: {str(e)}")

    conn.commit()
    conn.close()


# Seed data only if database is empty
conn = sqlite3.connect("diu_admissions.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM programs")
if c.fetchone()[0] == 0:
    seed_data()
conn.close()


# Pydantic Models
class Program(BaseModel):
    id: int
    name: str
    code: str
    department_code: str
    total_cost: float
    credits: int
    duration: float
    description: str
    eligibility: List[str]
    career_prospects: List[str]
    admission_deadline: str
    program_type: str
    accreditation: str


class WaiverInput(BaseModel):
    faculty: str
    ssc_gpa: float
    hsc_gpa: float
    is_new_student: bool = True
    current_sgpa: Optional[float] = 0.0
    student_profile: Optional[Dict] = {}


class WaiverOutput(BaseModel):
    id: str
    name: str
    category: str
    description: str
    waiver_percentage: str
    eligibility_criteria: List[str]
    required_documents: List[str]
    deadline: str
    applicable_programs: List[str]
    sgpa_required: float


class ApplicationInput(BaseModel):
    student_name: str
    email: str
    phone: str
    dob: str
    father_name: str
    mother_name: str
    nid: str
    gender: str
    program_code: str
    ssc_gpa: Optional[float]
    hsc_gpa: Optional[float]
    ssc_year: int
    hsc_year: int
    ssc_board: str
    hsc_board: str
    ssc_group: str
    hsc_group: str
    family_income: Optional[float]
    is_freedom_fighter_child: bool
    is_diu_employee_relative: bool
    has_sports_achievement: bool
    has_diploma: bool
    is_international_student: bool
    group_admission: bool
    documents_submitted: List[str]


class RecommendationInput(BaseModel):
    interests: List[str]
    academic_background: str
    career_goals: List[str]
    ssc_gpa: Optional[float] = 0.0
    hsc_gpa: Optional[float] = 0.0


class ChatInput(BaseModel):
    message: str
    session_id: str


# Waiver Calculator
class DIUWaiverCalculator:
    def __init__(self):
        self.waiver_data = self._load_waiver_data()

    def _load_waiver_data(self):
        with open("data/waivers.json") as f:
            return json.load(f)

    def calculate_waivers(
        self,
        faculty,
        ssc_gpa,
        hsc_gpa,
        is_new_student=True,
        current_sgpa=0,
        student_profile=None,
    ):
        if student_profile is None:
            student_profile = {}
        eligible = []
        for waiver in self.waiver_data:
            # Check if waiver applies to the faculty's programs
            conn = sqlite3.connect("diu_admissions.db")
            c = conn.cursor()
            c.execute("SELECT code FROM programs WHERE department_code = ?", (faculty,))
            program_codes = [row[0] for row in c.fetchall()]
            conn.close()
            if not any(code in waiver["applicable_programs"] for code in program_codes):
                continue

            # Parse waiver_rate (handle list or single value)
            waiver_rate = waiver["waiver_rate"]
            if isinstance(waiver_rate, list):
                waiver_percentage = max([int(r.strip("%")) for r in waiver_rate])
            else:
                waiver_percentage = int(waiver_rate.strip("%"))

            # Check eligibility
            meets_criteria = True
            criteria = waiver["eligibility_criteria"]
            if "SSC GPA 5.0" in criteria and ssc_gpa < 5.0:
                meets_criteria = False
            if "HSC GPA 5.0" in criteria and hsc_gpa < 5.0:
                meets_criteria = False
            if "HSC GPA 4.90-4.99" in criteria and (hsc_gpa < 4.90 or hsc_gpa > 4.99):
                meets_criteria = False
            if "Family income below 50,000 BDT/month" in criteria and (
                not student_profile.get("family_income")
                or student_profile["family_income"] >= 50000
            ):
                meets_criteria = False
            if "Child of freedom fighter" in criteria and not student_profile.get(
                "is_freedom_fighter_child"
            ):
                meets_criteria = False
            if (
                "DIU employee or immediate relative" in criteria
                and not student_profile.get("is_diu_employee_relative")
            ):
                meets_criteria = False
            if (
                "National or premier division sports achievement" in criteria
                and not student_profile.get("has_sports_achievement")
            ):
                meets_criteria = False
            if "Diploma in relevant field" in criteria and not student_profile.get(
                "has_diploma"
            ):
                meets_criteria = False
            if (
                "Group admission of 5 or more students" in criteria
                and not student_profile.get("group_admission")
            ):
                meets_criteria = False
            if "International student status" in criteria and not student_profile.get(
                "is_international_student"
            ):
                meets_criteria = False
            if (
                waiver["sgpa_required"] > 0
                and not is_new_student
                and current_sgpa < waiver["sgpa_required"]
            ):
                meets_criteria = False

            if meets_criteria:
                eligible.append(
                    {
                        "id": waiver["id"],
                        "name": waiver["name"],
                        "category": waiver["category"],
                        "description": waiver["description"],
                        "waiver_percentage": str(waiver_percentage) + "%",
                        "eligibility_criteria": criteria,
                        "required_documents": waiver["required_documents"],
                        "deadline": waiver["deadline"],
                        "applicable_programs": waiver["applicable_programs"],
                        "sgpa_required": waiver["sgpa_required"],
                    }
                )

        return sorted(
            eligible, key=lambda x: int(x["waiver_percentage"].strip("%")), reverse=True
        )


waiver_calculator = DIUWaiverCalculator()


# Routes
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/programs_page", response_class=HTMLResponse)
async def programs_page(request: Request):
    return templates.TemplateResponse("programs.html", {"request": request})


@app.get("/waivers_page", response_class=HTMLResponse)
async def waivers_page(request: Request):
    return templates.TemplateResponse("waivers.html", {"request": request})


@app.get("/recommendations_page", response_class=HTMLResponse)
async def recommendations_page(request: Request):
    return templates.TemplateResponse("recommendations.html", {"request": request})


@app.get("/application_page", response_class=HTMLResponse)
async def application_page(request: Request):
    return templates.TemplateResponse("application.html", {"request": request})


@app.get("/chat_page", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/dashboard_page", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/programs", response_model=List[Program])
async def get_programs():
    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()
    c.execute("SELECT * FROM programs")
    programs = [
        {
            "id": row[0],
            "name": row[1],
            "code": row[2],
            "department_code": row[3],
            "total_cost": row[4],
            "credits": row[5],
            "duration": row[6],
            "description": row[7],
            "eligibility": json.loads(row[8]),
            "career_prospects": json.loads(row[9]),
            "admission_deadline": row[10],
            "program_type": row[11],
            "accreditation": row[12],
        }
        for row in c.fetchall()
    ]
    conn.close()
    return programs


@app.post("/waivers/recommend", response_model=List[WaiverOutput])
async def recommend_waivers(input: WaiverInput):
    try:
        waivers = waiver_calculator.calculate_waivers(
            input.faculty,
            input.ssc_gpa,
            input.hsc_gpa,
            input.is_new_student,
            input.current_sgpa,
            input.student_profile,
        )
        return waivers
    except Exception as e:
        logger.error(f"Waiver calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommendations")
async def recommend_programs(input: RecommendationInput):
    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()
    c.execute("SELECT * FROM departments")
    departments = [
        {
            "id": row[0],
            "name": row[1],
            "code": row[2],
            "contact": row[3],
            "head": row[4],
            "description": row[5],
            "programs": json.loads(row[6]),
            "faculty": row[7],
            "location": row[8],
            "website": row[9],
            "established_year": row[10],
            "student_capacity": row[11],
            "accreditation": row[12],
        }
        for row in c.fetchall()
    ]
    conn.close()

    documents = [
        f"{d['description']} {' '.join(d['programs'])} {d['faculty']}"
        for d in departments
    ]
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), min_df=1, max_features=500
    )
    tfidf_matrix = vectorizer.fit_transform(documents)

    user_text = f"{' '.join(input.interests)} {input.academic_background} {' '.join(input.career_goals)}"
    user_vector = vectorizer.transform([user_text])

    similarities = cosine_similarity(user_vector, tfidf_matrix).flatten()

    recommendations = []
    avg_gpa = (
        (input.ssc_gpa + input.hsc_gpa) / 2 if input.ssc_gpa and input.hsc_gpa else 0
    )
    for i, dept in enumerate(departments):
        base_score = similarities[i]
        keyword_boost = 0
        for interest in input.interests:
            if (
                interest.lower() in dept["description"].lower()
                or interest.lower() in " ".join(dept["programs"]).lower()
            ):
                keyword_boost += 0.1
        for goal in input.career_goals:
            if goal.lower() in dept["description"].lower():
                keyword_boost += 0.1
        total_score = base_score + keyword_boost
        if total_score > 0.2:
            reasons = []
            matching_interests = [
                int
                for int in input.interests
                if int.lower() in dept["description"].lower()
                or int.lower() in " ".join(dept["programs"]).lower()
            ]
            if matching_interests:
                reasons.append(f"Matches interests: {', '.join(matching_interests)}")
            matching_goals = [
                goal
                for goal in input.career_goals
                if goal.lower() in dept["description"].lower()
            ]
            if matching_goals:
                reasons.append(f"Aligns with goals: {', '.join(matching_goals)}")
            recommendations.append(
                {
                    "department": {
                        "name": dept["name"],
                        "description": dept["description"],
                        "programs": dept["programs"],
                        "faculty": dept["faculty"],
                        "contact": dept["contact"],
                        "website": dept["website"],
                    },
                    "match_score": float(total_score),
                    "reasons": reasons or ["General match based on profile"],
                }
            )

    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    logger.info("Generated detailed department recommendations")
    return recommendations[:5]


@app.post("/applications")
async def submit_application(input: ApplicationInput):
    if (
        not validate_email(input.email)
        or not validate_phone(input.phone)
        or not validate_nid(input.nid)
    ):
        raise HTTPException(status_code=400, detail="Invalid input data")

    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()
    c.execute("SELECT * FROM programs WHERE code = ?", (input.program_code,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Program not found")

    c.execute(
        """
        INSERT INTO applications (
            student_name, email, phone, dob, father_name, mother_name, nid, gender, program_code,
            ssc_gpa, hsc_gpa, ssc_year, hsc_year, ssc_board, hsc_board, ssc_group, hsc_group, family_income,
            is_freedom_fighter_child, is_diu_employee_relative, has_sports_achievement,
            has_diploma, is_international_student, group_admission, documents_submitted,
            application_status, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            input.student_name,
            input.email,
            input.phone,
            input.dob,
            input.father_name,
            input.mother_name,
            input.nid,
            input.gender,
            input.program_code,
            input.ssc_gpa,
            input.hsc_gpa,
            input.ssc_year,
            input.hsc_year,
            input.ssc_board,
            input.hsc_board,
            input.ssc_group,
            input.hsc_group,
            input.family_income,
            input.is_freedom_fighter_child,
            input.is_diu_employee_relative,
            input.has_sports_achievement,
            input.has_diploma,
            input.is_international_student,
            input.group_admission,
            json.dumps(input.documents_submitted),
            "pending",
            datetime.now(),
        ),
    )
    app_id = c.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Application submitted: {app_id}")
    return {
        "id": app_id,
        "student_name": input.student_name,
        "program_code": input.program_code,
        "application_status": "pending",
    }


@app.post("/chat")
async def chat_with_bot(input: ChatInput):
    conn = sqlite3.connect("diu_admissions.db")
    c = conn.cursor()
    c.execute("SELECT question, answer, keywords FROM faqs")
    faqs = [
        {"question": row[0], "answer": row[1], "keywords": row[2]}
        for row in c.fetchall()
    ]
    conn.close()

    best_match = None
    highest_similarity = 0
    for faq in faqs:
        similarity = difflib.SequenceMatcher(
            None, input.message.lower(), faq["question"].lower()
        ).ratio()
        keyword_similarity = (
            max(
                [
                    difflib.SequenceMatcher(
                        None, input.message.lower(), kw.lower()
                    ).ratio()
                    for kw in faq["keywords"].split(", ")
                ]
            )
            if faq["keywords"]
            else 0
        )
        total_similarity = max(similarity, keyword_similarity)
        if total_similarity > highest_similarity:
            highest_similarity = total_similarity
            best_match = faq["answer"]

    if highest_similarity > 0.4:
        return {"response": best_match}
    return {
        "response": "Sorry, I couldn't find an answer to your question. Please try rephrasing or contact support."
    }


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$", email))


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^(?:\+880|880|0)?1[3-9]\d{8}$", phone))


def validate_nid(nid: str) -> bool:
    nid = "".join(filter(str.isdigit, nid))
    return len(nid) >= 10


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
