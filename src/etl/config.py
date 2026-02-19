"""
Configuration for Singapore Jobs ETL Pipeline
All constants, mappings, and thresholds
"""

import os

# ============================================================================
# FILE PATHS
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

PATHS = {
    "raw":    os.path.join(BASE_DIR, "data/raw/SGJobData.csv"),
    "bronze": os.path.join(BASE_DIR, "data/bronze/sg_jobs_bronze.parquet"),
    "silver": os.path.join(BASE_DIR, "data/silver/sg_jobs_silver.parquet"),
    "gold":   os.path.join(BASE_DIR, "data/gold/"),
}

# ============================================================================
# SALARY CLEANING PARAMETERS
# ============================================================================

SALARY_FLOOR = 500          # Monthly SGD — below this is bad data
SALARY_CEILING = 50_000     # Monthly SGD — above this is bad data
WINSOR_PERCENTILES = (0.01, 0.99)  # 1st and 99th percentile

# IQR multiplier for outlier flagging (standard is 1.5)
IQR_MULTIPLIER = 1.5

# ============================================================================
# SENIORITY MAPPING (9 levels → 4 tiers)
# ============================================================================

SENIORITY_MAP = {
    "Fresh/entry level": "Entry",
    "Non-executive":     "Entry",
    "Junior Executive":  "Mid",
    "Executive":         "Mid",
    "Professional":      "Senior",
    "Senior Executive":  "Senior",
    "Manager":           "Management",
    "Middle Management": "Management",
    "Senior Management": "Management",
}

# ============================================================================
# EXPERIENCE BANDS
# ============================================================================

EXPERIENCE_BANDS = [
    (0, 1,   "0-1 yr"),
    (2, 3,   "2-3 yrs"),
    (4, 5,   "4-5 yrs"),
    (6, 10,  "6-10 yrs"),
    (11, 999, "10+ yrs"),
]

# Cap for unrealistic experience values
MAX_EXPERIENCE_YEARS = 30

# ============================================================================
# ROLE FAMILY KEYWORDS (ordered by specificity)
# ============================================================================

ROLE_KEYWORDS = {
    # Most specific roles first
    "Healthcare":  ["nurse", "doctor", "medical", "clinical", "healthcare", "pharmacy", "therapist"],
    "Education":   ["teacher", "educator", "trainer", "lecturer", "tutor", "instructor"],

    # Technical roles
    "Developer":   ["developer", "programmer", "software", "frontend", "backend", "fullstack", "full stack", "full-stack"],
    "Engineer":    ["engineer", "engineering", "technician", "mechanic", "maintenance"],
    "Analyst":     ["analyst", "analytics", "data scientist", "insight", "research"],
    "IT/Systems":  ["it support", "infrastructure", "network", "system admin", "cloud", "devops", "cybersecurity", "security analyst"],

    # Business functions
    "Finance":     ["finance", "accounting", "accountant", "audit", "tax", "treasury"],
    "HR":          ["hr ", "human resource", "talent acquisition", "recruitment", "recruiter", "people"],
    "Marketing":   ["marketing", "brand", "content", "social media", "digital marketing", "seo", "sem"],
    "Sales":       ["sales", "business development", "account manager", "account executive", "relationship manager"],

    # General leadership (less specific)
    "Manager":     ["manager", "head of", "director", "vp ", "vice president", "chief", "lead"],
    "Consultant":  ["consultant", "advisor", "advisory"],

    # Operational roles
    "Operations":  ["operations", "logistics", "supply chain", "procurement", "warehouse", "inventory"],
    "Admin":       ["admin", "secretary", "coordinator", "clerk", "receptionist", "assistant"],
    "Retail/F&B":  ["cashier", "barista", "chef", "cook", "server", "waiter", "retail", "outlet", "店员"],
    "Driver":      ["driver", "delivery", "dispatch", "courier", "rider"],
}

# ============================================================================
# DATA QUALITY THRESHOLDS (for warnings)
# ============================================================================

MIN_EXPECTED_ROWS = 1_000_000
MAX_BRONZE_TO_SILVER_LOSS_PCT = 0.10  # Warn if >10% rows lost
