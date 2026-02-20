# 🇸🇬 Singapore Jobs Analytics Dashboard

Comprehensive analytics dashboard for 1M+ Singapore job postings (Oct 2022 – Apr 2023).
Built with Medallion architecture (Bronze → Silver → Gold) and multi-persona Streamlit dashboard.
Preview dashboard at https://ceddcbcqdhcudd-sgjobanalytics.streamlit.app/

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (environment.yml specifies 3.10, tested with Python 3.14.2)
- 8GB+ RAM recommended
- Conda or pip

### Installation

**Option A: Using Conda (Recommended)**

1. **Create conda environment from environment.yml**
   ```bash
   conda env create -f environment.yml
   conda activate sg_job_analytics
   ```

2. **Navigate to project directory**
   ```bash
   cd /path/to/sg_job_analytics
   ```

3. **Place raw data**
   ```
   data/raw/SGJobData.csv
   ```

**Option B: Using pip**

1. **Create virtual environment**
   ```bash
   python -m venv sg_job_analytics_env
   source sg_job_analytics_env/bin/activate  # On Windows: sg_job_analytics_env\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Navigate to project directory**
   ```bash
   cd /path/to/sg_job_analytics
   ```

4. **Place raw data**
   ```
   data/raw/SGJobData.csv
   ```

**Option C: Update existing Conda environment**

If you already have a conda environment and want to add these dependencies:
```bash
conda env update -f environment.yml --prune
conda activate sg_job_analytics
```

---

## 📊 Usage

### Option 1: Run Complete ETL Pipeline

```python
from src.etl.sg_jobs_etl import SGJobsETL

etl = SGJobsETL()
etl.run_all()  # Bronze → Silver → Gold (1-2 minutes)
```

**What happens:**
- **Bronze**: Removes synthetic rows, nulls, useless columns → `data/bronze/sg_jobs_bronze.parquet` (49 MB)
- **Silver**: Parses industries, maps seniority, cleans salaries, extracts roles → `data/silver/sg_jobs_silver.parquet` (63 MB)
- **Gold**: Generates 6 aggregate tables → `data/gold/*.parquet`

### Option 2: Explore Step-by-Step in Notebooks

1. `notebooks/01_bronze.ipynb` — Data cleaning and quality checks
2. `notebooks/02_silver.ipynb` — Feature engineering and EDA
3. `notebooks/03_gold.ipynb` — Business aggregations

### Option 3: Launch Dashboard (ETL must be run first)

```bash
streamlit run app/Home.py
```

Access at: http://localhost:8501

---

## 🎯 Dashboard Personas

### 🎯 Career Switcher
**For:** Professionals exploring new industries

**Features:**
- Compare industries side-by-side
- Salary benchmarking by role & seniority
- Competition analysis (applications per vacancy)
- Experience requirements mapping

**Use Cases:**
- "Should I switch from IT to Finance?"
- "What's the salary range for Data Analysts in Banking?"
- "How competitive is the Healthcare sector?"

---

### 💼 Talent Acquisition
**For:** HR teams & recruiters

**Features:**
- Market salary benchmarks by role × seniority
- Top hiring companies ranked
- Hard-to-fill role indicators (repost rates, competition ratios)
- Posting velocity trends

**Use Cases:**
- "What salary should I offer for a Senior Engineer?"
- "Which companies are hiring aggressively for Sales roles?"
- "Is this role hard to fill in the current market?"

---

### 📈 Policy Analyst
**For:** Government agencies & researchers

**Features:**
- Sector growth indices (indexed posting volume)
- Employment type shifts over time
- Vacancy-application gaps (labor market balance)
- Labor market macro trends

**Use Cases:**
- "Which sectors are growing fastest?"
- "Are full-time roles declining?"
- "Which industries have labor shortages?"

---

## 🏗️ Architecture

### Medallion Pipeline

#### Bronze (Raw → Clean)
- Remove synthetic test data (10 rows with $23.7M salaries)
- Drop row-wide nulls (3,988 rows)
- Remove useless columns (`occupationId`, `status_id`, `salary_type`)
- Type casting (dates, integers, floats)

**Output:** 1,044,587 rows × 19 columns

---

#### Silver (Clean → Enriched)
- **Parse JSON categories** → `industry_list`, `primary_industry`
- **Map position levels** → 4 seniority tiers (Entry, Mid, Senior, Management)
- **Three-stage salary cleaning**:
  1. Hard bounds ($500 - $50,000)
  2. IQR outlier flagging (preserve data)
  3. Winsorization at 1st/99th percentile
- **Extract role families** → 17 families via keyword matching
- **Derive features** → `competition_ratio`, `experience_band`, `annual_salary_clean`
- **Optimize memory** → Category dtypes (38.6% savings: 1GB → 635MB)

**Output:** 1,044,587 rows × 38 columns

---

#### Gold (Enriched → Aggregated)
Six business aggregate tables optimized for dashboard queries:

| Table | Grain | Purpose |
|-------|-------|---------|
| `agg_monthly_postings` | month × industry | Posting trends over time |
| `agg_salary_by_role` | role × seniority × industry | Salary benchmarks |
| `agg_industry_demand` | industry | Industry-level KPIs |
| `agg_competition` | industry × role | Competition metrics |
| `agg_top_companies` | company × primary_industry | Company hiring activity |
| `agg_experience_demand` | industry × experience × seniority | Experience requirements |

---

## 📁 Project Structure

```
sg_job_analytics/
├── data/
│   ├── raw/              # SGJobData.csv (user-provided)
│   ├── bronze/           # sg_jobs_bronze.parquet (49 MB)
│   ├── silver/           # sg_jobs_silver.parquet (63 MB)
│   └── gold/             # 6 aggregate parquet files
├── src/etl/
│   ├── config.py         # Constants and mappings
│   └── sg_jobs_etl.py    # SGJobsETL class
├── notebooks/            # Annotated EDA notebooks
│   ├── 01_bronze.ipynb
│   ├── 02_silver.ipynb
│   └── 03_gold.ipynb
├── app/                  # Streamlit dashboard
│   ├── streamlit_app.py  # Home page
│   └── pages/
│       ├── 1_Career_Switcher.py
│       ├── 2_Talent_Acquisition.py
│       └── 3_Policy_Analyst.py
├── tests/                # Unit tests
│   ├── conftest.py
│   └── test_transformations.py
├── requirements.txt
├── README.md
└── final_report.md       # Assignment deliverable
```

---

## ⚙️ Configuration

Override defaults via constructor:

```python
etl = SGJobsETL(config_override={
    'SALARY_FLOOR': 1000,  # Custom floor
    'SALARY_CEILING': 60000,  # Custom ceiling
    'WINSOR_PERCENTILES': (0.05, 0.95),  # 5th/95th percentile
})

etl.run_all()
```

See `src/etl/config.py` for all configurable parameters:
- Salary thresholds
- Seniority mapping (9 → 4 tiers)
- Experience bands
- Role keywords (16 families)
- Data quality thresholds

---

## 🧪 Testing

```bash
pip install pytest pytest-cov
pytest tests/ -v
```

**Tests cover:**
- Seniority mapping completeness
- Salary cleaning (bounds, swaps, divide-by-zero)
- Role extraction priority
- Category JSON parsing
- Experience band assignment
- Configuration validation

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **ETL Runtime** | 1-2 minutes (1M rows) |
| **Dashboard Load** | <5 seconds |
| **Memory Usage** | ~400MB peak (Silver layer) |
| **File Compression** | CSV 273MB → Bronze 49MB → Silver 63MB (77% reduction) |

---

## 🗂️ Data Schema

### Silver Layer (Row-Level)
- **Rows:** 1,044,587
- **Columns:** 38
- **Date range:** 2022-10-01 to 2023-04-30
- **Key features:** `role_family`, `seniority_tier`, `average_salary_clean`, `competition_ratio`, `experience_band`

### Gold Layer (Aggregates)
- **Tables:** 6
- **Total rows:** ~2.3M (company-level table is largest)
- **File size:** ~15 MB total
- **Optimized for:** Dashboard queries via Streamlit `@st.cache_data`

---

## 📝 Known Data Issues & Handling

| Issue | Location | Treatment |
|-------|----------|-----------|
| Synthetic rows (`RANDOM_JOB_` prefix) | Bronze | Filtered with dual validation (prefix + salary check) |
| Row-wide nulls (3,988 rows) | Bronze | Dropped where `title` is null |
| `occupationId` 100% null | Bronze | Column dropped |
| Salary outliers (>$50k/month) | Silver | Three-stage cleaning (Bounds → IQR → Winsorization) |
| `minimumYearsExperience` max=88 | Silver | Capped at 30 before banding |
| Multiple industries per posting | Gold | **Exploded** for industry-level aggregates; `agg_top_companies` uses `primary_industry` only |

---

## 💡 Tips & Tricks

### Tuning Salary Parameters

If you want to adjust salary cleaning:

1. **Run Silver with diagnostics:**
   ```python
   etl = SGJobsETL()
   etl.run_silver()
   ```

2. **Review distributions in `02_silver.ipynb`** (Parameter Tuning section)

3. **Update `src/etl/config.py`:**
   ```python
   SALARY_FLOOR = 300  # Adjusted down
   IQR_MULTIPLIER = 2.0  # More conservative
   ```

4. **Rerun Silver:**
   ```python
   etl.run_silver()  # Regenerates with new parameters
   ```

### Exporting Silver Data

The Silver parquet is your **final cleaned dataset** - shareable and ready for custom analysis:

```python
import pandas as pd
df = pd.read_parquet('data/silver/sg_jobs_silver.parquet')

# Export to CSV (if needed)
df.to_csv('data/silver/sg_jobs_silver.csv', index=False)

# Export subset to Excel (Excel has 1M row limit)
df.head(1_000_000).to_excel('data/silver/sg_jobs_sample.xlsx', index=False)
```

### Custom Dashboard Filters

Edit `app/pages/*.py` to add custom filters or charts using the Gold tables.

---

## 🐛 Troubleshooting

**Problem:** `FileNotFoundError: data/raw/SGJobData.csv`
**Solution:** Place the CSV file in `data/raw/` directory

**Problem:** `Module not found: streamlit`
**Solution:** Run `pip install -r requirements.txt`

**Problem:** Dashboard shows "No data"
**Solution:** Run ETL pipeline first: `etl.run_all()`

**Problem:** Out of memory during ETL
**Solution:** Close other applications; Silver uses ~400MB peak

**Problem:** Tests fail with `pytest not found`
**Solution:** Install pytest: `pip install pytest`

---

## 📚 Documentation

- **Assignment requirements:** `assignment_requirements.md`
- **Implementation plan:** `implementation_plan.md`
- **Final report:** `final_report.md` (assignment deliverable)
- **Decisions log:** `questions.md`

---

## 🤝 Contributing

This is an assignment project. For improvements:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📄 License

Assignment project — not for commercial use.

---

## 🙏 Acknowledgments

- **Data Source:** Singapore Jobs Dataset (Oct 2022 - Apr 2023)
- **Tools:** Python, Pandas, Streamlit, Plotly, Seaborn
- **Architecture:** Medallion (Bronze → Silver → Gold)
- **Built with:** Claude Code

---

## 📧 Contact

For questions or issues, please open an issue in the repository.

---

**🤖 Generated with Claude Code | Last Updated:** 2026-02-18
