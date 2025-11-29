# ----------------------------------------------------------
#  S C H E M E L Y   -   BACKEND  API   (FINAL FIXED VERSION)
# ----------------------------------------------------------

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import re
import io
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ----------------------------------------------------------
#  FLASK INITIALIZATION
# ----------------------------------------------------------

app = Flask(__name__)
CORS(app)


# ----------------------------------------------------------
#  LOAD DATASET FROM GOOGLE DRIVE
# ----------------------------------------------------------

DRIVE_FILE_ID = "1zCcZjIIjDWmNDfSTZ1eeBD6z98uOaSw7"
CSV_URL = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"

REQUIRED_COLS = [
    "Scheme_Name","Min_Age","Max_Age","Gender_Eligibility","Min_Education",
    "Area","State","Target_Group","Application_Link","Summary"
]

def load_dataset(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""
    df["Min_Age"] = pd.to_numeric(df["Min_Age"], errors="coerce")
    df["Max_Age"] = pd.to_numeric(df["Max_Age"], errors="coerce")
    return df

DF = load_dataset(CSV_URL)


def fix_defaults(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Min_Age"] = df["Min_Age"].fillna(0)
    df["Max_Age"] = df["Max_Age"].replace(0, None).fillna(200)
    df["Gender_Eligibility"] = df["Gender_Eligibility"].replace("", "any")
    df["Min_Education"] = df["Min_Education"].replace("", "any")
    df["Area"] = df["Area"].replace("", "any")
    df["State"] = df["State"].replace("", "any")
    df["Target_Group"] = df["Target_Group"].fillna("")
    df["Summary"] = df["Summary"].fillna("")
    df["Application_Link"] = df["Application_Link"].fillna("")
    df["Scheme_Name"] = df["Scheme_Name"].fillna("")
    return df

DF = fix_defaults(DF)


# ----------------------------------------------------------
#  RULES & FILTERING
# ----------------------------------------------------------

EDU_ORDER = ["class 8","class 10","class 12","graduate","postgraduate","phd","any"]
EDU_RANK  = {e:i for i,e in enumerate(EDU_ORDER)}

TAG_KEYWORDS = {
    "Student":      ["student","scholar","nsp","inspire","school","college"],
    "Unemployed":   ["unemployed","rojgar","ncs","employment"],
    "Youth":        ["youth","skill","pmkvy","apprentice","internship"],
    "Women":        ["women","woman","mahila","beti","kanya","ladli","girl"],
    "Entrepreneur": ["startup","entrepreneur","mudra","pmegp","odop","udyam","pm-fme","msme"],
    "Farmer":       ["farmer","kisan","agri","agriculture","crop","horticulture","irrigation","dairy","bamboo","rythu"]
}

INDIAN_STATES = [
    "andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh","goa",
    "gujarat","haryana","himachal pradesh","jharkhand","karnataka","kerala",
    "madhya pradesh","maharashtra","manipur","meghalaya","mizoram","nagaland",
    "odisha","orissa","punjab","rajasthan","sikkim","tamil nadu","telangana",
    "tripura","uttar pradesh","uttarakhand","west bengal","delhi","ladakh",
    "jammu","kashmir","jammu and kashmir"
]

@dataclass
class Profile:
    age: int
    gender: str
    education: str
    area: str
    state: str
    tags: List[str]


def norm(x) -> str:
    try: return str(x).lower().strip()
    except: return ""


def is_central(state: str) -> bool:
    s = norm(state)
    return s in ("", "any") or "all india" in s or "pan india" in s


def edu_ok(user_ed: str, req_ed: str) -> bool:
    req = norm(req_ed)
    if req not in EDU_RANK:
        return True
    return EDU_RANK.get(norm(user_ed), -1) >= EDU_RANK[req]


def gender_ok(row_gender: str, user_gender: str) -> bool:
    g = norm(row_gender)
    return g in ("", "any") or g == norm(user_gender)


def link_score(link: str) -> float:
    host = urlparse(str(link)).netloc.lower()
    if host.endswith(".gov.in") or host.endswith(".nic.in"):
        return 2.0
    if host.endswith(".gov") or host.endswith(".org"):
        return 1.0
    return 0.3


def combined_text(row: pd.Series) -> str:
    text = norm(row["Scheme_Name"]) + " " + norm(row["Summary"]) + " " + norm(row["Target_Group"])
    return re.sub(r"[^a-z]", "", text)


def is_health_scheme(row: pd.Series) -> bool:
    text = combined_text(row)
    words = ["health","disease","hospital","mental","virus","cancer","medical","ayush","covid"]
    return any(w in text for w in words)


def is_agri_scheme(row: pd.Series) -> bool:
    text = combined_text(row)
    words = ["kisan","farmer","agri","crop","irrigation","dairy","bamboo","rythu"]
    return any(w in text for w in words)


def is_other_state_specific(row: pd.Series, u: Profile) -> bool:
    name = norm(row["Scheme_Name"])
    u_state = norm(u.state)
    mentioned = [s for s in INDIAN_STATES if s in name]
    if not mentioned: return False
    for st in mentioned:
        if st not in u_state and u_state not in st:
            return True
    return False


def tag_hit(row: pd.Series, u: Profile) -> bool:
    text = norm(row["Scheme_Name"]) + " " + norm(row["Summary"]) + " " + norm(row["Target_Group"])
    for t in u.tags:
        for kw in TAG_KEYWORDS.get(t, []):
            if kw in text:
                return True
    return False


def passes_core_filters(row: pd.Series, u: Profile) -> bool:
    if not is_central(row["State"]) and norm(u.state) not in norm(row["State"]):
        return False
    if not (row["Min_Age"] <= u.age <= row["Max_Age"]):
        return False
    if not edu_ok(u.education, row["Min_Education"]):
        return False
    if not gender_ok(row["Gender_Eligibility"], u.gender):
        return False
    return True


def allowed_category(row: pd.Series, u: Profile) -> bool:
    if is_health_scheme(row):
        if ("Pregnant Women" not in u.tags and "Senior Citizen" not in u.tags):
            return False
    if is_agri_scheme(row):
        if "Farmer" not in u.tags:
            return False
    if is_other_state_specific(row, u):
        return False
    return True


def strong_match(row, u): return tag_hit(row, u)
def mild_match(row, u): return tag_hit(row, u) or gender_ok(row["Gender_Eligibility"], u.gender)


def score_row(row: pd.Series, u: Profile) -> float:
    s = 0.0
    if gender_ok(row["Gender_Eligibility"], u.gender): s += 3
    if is_central(row["State"]): s += 3
    if tag_hit(row, u): s += 2
    s += link_score(row["Application_Link"])
    return s


def recommend_schemes(df: pd.DataFrame, u: Profile, k: int = 5) -> pd.DataFrame:
    df = df.copy()

    strong_mask = df.apply(lambda r: passes_core_filters(r, u) and 
                                      allowed_category(r, u) and 
                                      strong_match(r, u), axis=1)
    strong = df[strong_mask].copy()

    if not strong.empty:
        strong["__score"] = strong.apply(lambda r: score_row(r, u), axis=1)
        strong = strong.sort_values("__score", ascending=False)

    base = strong
    need = k - len(base)

    if need > 0:
        mild_mask = df.apply(lambda r: passes_core_filters(r, u) and 
                                        allowed_category(r, u) and 
                                        mild_match(r, u), axis=1)
        mild = df[mild_mask].copy()
        mild = mild[~mild["Scheme_Name"].isin(base["Scheme_Name"])]
        if not mild.empty:
            mild["__score"] = mild.apply(lambda r: score_row(r, u), axis=1)
            mild = mild.sort_values("__score", ascending=False).head(need)
            base = pd.concat([base, mild], ignore_index=True)

    need = k - len(base)

    if need > 0:
        core_mask = df.apply(lambda r: passes_core_filters(r, u) and 
                                        allowed_category(r, u), axis=1)
        core = df[core_mask].copy()
        core = core[~core["Scheme_Name"].isin(base["Scheme_Name"])]
        if not core.empty:
            core["__score"] = core.apply(lambda r: score_row(r, u), axis=1)
            core = core.sort_values("__score", ascending=False).head(need)
            base = pd.concat([base, core], ignore_index=True)

    if base.empty:
        return base

    return base.head(k).drop(columns=["__score"], errors="ignore")


# ----------------------------------------------------------
#  HEALTH CHECK
# ----------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ----------------------------------------------------------
#  MAIN RECOMMENDER ENDPOINT
# ----------------------------------------------------------

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True)

    try:
        age = int(data.get("age", 0))
    except:
        age = 0

    profile = Profile(
        age=age,
        gender=data.get("gender","").lower(),
        education=data.get("education","").lower(),
        area=data.get("area","").lower(),
        state=data.get("state","").lower(),
        tags=[t.title() for t in data.get("tags", [])]
    )

    top = recommend_schemes(DF, profile, k=10)

    out = []
    for _, row in top.reset_index(drop=True).iterrows():
        out.append({
            "scheme_name": row["Scheme_Name"],
            "state": row["State"],
            "summary": row["Summary"],
            "link": row["Application_Link"],
            "target_group": row["Target_Group"]
        })

    return jsonify({"count": len(out), "results": out})


# ----------------------------------------------------------
#  PDF DOWNLOAD ENDPOINT  (NOW WORKS)
# ----------------------------------------------------------

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    data = request.get_json(force=True)
    schemes = data.get("schemes", [])

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Schemely - Recommended Policies")
    y -= 30

    pdf.setFont("Helvetica", 11)

    for s in schemes:
        if y < 80:
            pdf.showPage()
            y = 750
            pdf.setFont("Helvetica", 11)

        pdf.drawString(50, y, f"• {s.get('scheme_name', '')}")
        y -= 15

        pdf.drawString(60, y, f"Summary: {s.get('summary','')[:250]}")
        y -= 15

        pdf.drawString(60, y, f"State: {s.get('state','')}")
        y -= 15

        pdf.drawString(60, y, f"Apply: {s.get('link','')}")
        y -= 25

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="schemes.pdf",
        mimetype="application/pdf"
    )


# ----------------------------------------------------------
#  START FLASK SERVER
# ----------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)


