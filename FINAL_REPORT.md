# Singapore Jobs Analytics — Final Report
## Module 1 Assignment Project

**Date:** February 18, 2026
**Dataset:** Singapore Job Postings (Oct 2022 - Apr 2023)
**Data Size:** 1,048,585 rows × 22 columns (273 MB CSV)

---

## 1. Business Case

### Business Scenario
The Singapore job market is dynamic and complex, with multiple stakeholders requiring different analytical perspectives on the same underlying data. This project addresses the information needs of three distinct user groups through a unified multi-persona analytics dashboard.

### Objective
**Enable data-driven decision-making across career planning, talent acquisition, and labor policy domains by providing role-specific insights from Singapore job market data.**

Specific problems addressed:
1. **Career Switchers:** "Which industry should I transition to for better salary and opportunities?"
2. **Talent Acquisition Teams:** "What salary should I offer, and how competitive is this role?"
3. **Policy Analysts:** "Which sectors are growing, and where are labor market imbalances?"

### Target Users and Value

| Persona | User Profile | Value Delivered |
|---------|-------------|-----------------|
| **🎯 Career Switcher** | Mid-career professionals exploring industry pivots | Benchmarked salary expectations, competition analysis, role availability insights for confident career transitions |
| **💼 Talent Acquisition** | HR managers, recruiters, hiring teams | Market-competitive salary data, hard-to-fill role indicators, competitive intelligence for effective recruitment strategies |
| **📈 Policy Analyst** | Government agencies, workforce development orgs, researchers | Macro labor market trends, sector growth indices, employment type shifts for evidence-based policy formulation |

**Key Value Proposition:** Transform 1M+ raw job postings into actionable, persona-specific insights that reduce decision uncertainty and enable data-driven strategies.

---

## 2. Data Handling & Process

### Tools Used
- **Python 3.14.2** for all data processing
- **Pandas 2.x** for data manipulation and aggregation
- **Streamlit 1.28+** for interactive dashboard
- **Plotly 5.x** for interactive visualizations
- **Seaborn 0.12** for statistical plots
- **PyArrow 12+** for Parquet file I/O
- **Jupyter** for exploratory data analysis and documentation

### Loading the CSV (~1M+ rows)
```python
df = pd.read_csv('SGJobData.csv',
                 dtype={'numberOfVacancies': 'Int64', ...},  # Explicit dtypes
                 low_memory=False)
# Result: 1,048,585 rows × 22 columns, 273 MB
```

**Challenges:** Large file size required careful memory management and type specification upfront to prevent dtype inference errors.

### Key Cleaning Steps

#### 1. **Remove Synthetic Test Data**
- **Issue:** 10 rows with prefix `RANDOM_JOB_` contained anomalous salaries ($23.7M/month)
- **Solution:** Dual-validation filter (prefix match + salary verification)
- **Result:** 10 rows removed with logged confirmation of anomalous values

#### 2. **Drop Row-Wide Nulls**
- **Issue:** 3,988 rows (0.38%) had nulls across all meaningful columns
- **Solution:** Filter where `title.isna()` as primary indicator
- **Result:** 3,988 rows removed, 1,044,587 clean rows retained

#### 3. **Remove Useless Columns**
- **Issue:** `occupationId` (100% null), `status_id` (constant=0), `salary_type` (constant='Monthly')
- **Solution:** Column-level drop in Bronze layer
- **Result:** Reduced from 22 to 19 columns

#### 4. **Parse JSON Categories**
- **Issue:** `categories` field stored as JSON string: `'[{"id":21,"category":"IT"}]'`
- **Solution:** Custom parser with fallback:
  ```python
  categories = json.loads(cat_string)
  industry_list = [item['category'] for item in categories]
  primary_industry = industry_list[0] if industry_list else 'Unknown'
  ```
- **Result:** 43 unique industries identified, avg 1.69 industries per posting

#### 5. **Three-Stage Salary Cleaning**
This was the most complex transformation:

**Stage 1: Hard Business Bounds**
- Null out salaries < $500 or > $50,000/month (clear bad data)
- Fix inverted min/max (e.g., min=$5k, max=$3k → swap)
- Removed: 9,831 salaries outside bounds

**Stage 2: IQR Outlier Flagging**
- Calculate IQR (Q3 - Q1) on remaining valid salaries
- Flag outliers beyond Q1 - 1.5×IQR and Q3 + 1.5×IQR
- **Preserve data** but mark for analysis (70,684 outliers flagged)

**Stage 3: Winsorization**
- Clip salaries to 1st and 99th percentiles ($1,150 - $16,500)
- Create `average_salary_clean` for reliable aggregations
- Prevents extreme outliers from skewing mean/median calculations

**Rationale:** Preserve data integrity while reducing skew impact on business metrics.

### Important Feature Engineering

#### 1. **Seniority Tier Mapping (9 → 4)**
- Consolidated fragmented position levels into actionable tiers
- Mapping: `{Fresh/Entry: "Entry", Executive: "Mid", Manager: "Management", ...}`
- Result: 40.3% Mid, 24.0% Entry, 20.4% Senior, 15.3% Management

#### 2. **Role Family Extraction**
- **Challenge:** No standardized role classification in raw data
- **Solution:** Keyword-based matching with priority ordering (specific before generic)
  ```python
  ROLE_KEYWORDS = {
      "Healthcare": ["nurse", "doctor", "medical"],  # Specific first
      "Manager": ["manager", "director", "vp"],       # Generic last
  }
  ```
- **Result:** 17 role families classified (top: Other 32%, Engineer 15%, Manager 13%)

#### 3. **Competition Ratio**
- **Formula:** `applications / vacancies`
- **Handling:** Null for vacancies=0 (avoid divide-by-zero)
- **Insight:** Avg 1.67 applications per vacancy (market competitiveness indicator)

#### 4. **Experience Bands**
- Binned `minimumYearsExperience` into 5 actionable bands: 0-1yr, 2-3yrs, 4-5yrs, 6-10yrs, 10+yrs
- Capped unrealistic values (max=88 → capped at 30)

#### 5. **Memory Optimization**
- Converted low-cardinality strings to `category` dtype
- Result: **38.6% memory savings** (1,034 MB → 635 MB)

### EDA Highlights

#### Key Patterns Discovered

**1. Salary Distribution is Right-Skewed**
- Median: $4,000/month
- Mean: $5,200/month (pulled up by high earners)
- Winsorization bounds: $1,150 - $16,500 (1st-99th percentile)
- **Impact on Design:** Use median (not mean) for salary benchmarks in dashboard

**2. Industry Concentration**
- Top 3 industries account for 40% of postings
- Information Technology, Sales, Admin dominate
- **Impact on Design:** Default filters to top industries for faster initial load

**3. Seniority Pyramid**
- Most demand at Mid level (40.3%), fewer at Entry (24%)
- Suggests market favors experienced talent
- **Impact on Design:** Career Switcher persona shows seniority-specific competition

**4. Competition Varies Widely**
- Some roles: 0.5 applications/vacancy (hard to fill)
- Others: 10+ applications/vacancy (over-subscribed)
- **Impact on Design:** Talent Acquisition persona flags hard-to-fill roles

**5. Multi-Industry Tagging**
- 69% of postings tagged to multiple industries
- **Decision:** Explode industries in Gold aggregates (accept double-counting), use `primary_industry` for company-level metrics to avoid inflation

---

## 3. Dashboard / App

### Type of Solution
**Streamlit Multi-Page Dashboard** — Python-based interactive web application deployed locally.

**Rationale:**
- Rapid prototyping with native Python integration
- Built-in caching (`@st.cache_data`) for fast reloads
- Multi-page architecture for persona separation
- No front-end coding required (focus on analytics)

### Main Views

#### **Home Page: Market Overview**
- **Purpose:** High-level KPIs and persona navigation
- **Metrics Row:**
  - Total Postings: 1,044,587
  - Total Vacancies: 2,804,714
  - Unique Industries: 43
  - Date Range: Oct 2022 - Apr 2023
- **Charts:**
  - Top 10 industries (horizontal bar, sorted)
  - Employment type breakdown (donut chart)
  - Monthly posting trend (line chart)
- **Persona Cards:** 3 clickable cards with descriptions + navigation links

#### **Page 1: Career Switcher**
**Audience:** Professionals exploring industry transitions

**Filters (Sidebar):**
- From Industry (dropdown)
- To Industry (dropdown)
- Seniority Tier (dropdown)
- Min Years Experience (slider)

**Views:**
1. **Side-by-Side Industry Comparison**
   - 2 columns showing origin vs target industry KPIs
   - Metrics: postings, salary, competition, repost rate
   - Enables direct comparison for transition assessment

2. **Role Availability in Target Industry**
   - Horizontal bar chart (top 15 roles by posting count)
   - Color-coded by competition ratio (red=high, green=low)
   - **Value:** Shows which roles have most opportunities

3. **Salary Benchmarker**
   - Box plot showing 25th-75th percentile salary range by role
   - Filtered by selected seniority + industry
   - **Value:** Sets realistic salary expectations

4. **Competition Intensity**
   - Bar chart: median competition ratio by role
   - Higher ratio = easier to get hired (more applicants per vacancy)
   - **Value:** Identifies low-competition entry points

5. **Experience Requirements**
   - Bar chart: postings by experience band
   - **Value:** Validates if user's experience matches market demand

#### **Page 2: Talent Acquisition**
**Audience:** HR managers and recruiters

**Filters (Sidebar):**
- Role Family (dropdown)
- Industry (dropdown, "All" option)
- Seniority Tiers (multi-select)

**Views:**
1. **Market Salary Benchmark**
   - Box plot: salary range by seniority for selected role
   - Optional input: user's offer salary for instant comparison
   - **Value:** Validates compensation competitiveness

2. **Top Hiring Companies**
   - Horizontal bar: top 15 companies by posting count
   - Color intensity = avg salary offered
   - Filtered to companies with ≥5 postings (Q13 Decision)
   - **Value:** Competitive intelligence, poaching targets

3. **Hard-to-Fill Indicators**
   - 4 KPI metrics:
     - Avg competition ratio (applications/vacancy)
     - Market repost rate (% jobs reposted)
     - Avg applications per posting
     - Total market demand (posting count)
   - **Value:** Assesses recruitment difficulty upfront

4. **Posting Velocity Trend**
   - Line chart: monthly posting count for selected role
   - Trend indicator: "📈 Increasing" or "📉 Decreasing"
   - **Value:** Times recruitment campaigns to market activity

5. **Seniority Mix**
   - Donut chart: % of postings by seniority tier
   - **Value:** Aligns recruitment targets with market hiring patterns

#### **Page 3: Policy Analyst**
**Audience:** Government agencies, researchers

**Filters (Sidebar):**
- Industries (multi-select, default: top 10)
- Date Range (slider over posting months)

**Views:**
1. **Sector Growth Index**
   - Line chart: posting volume indexed to first month = 100
   - One line per selected industry
   - **Value:** Identifies growing vs declining sectors for upskilling priorities

2. **Employment Type Dynamics**
   - Stacked area chart: % share of Full Time / Contract / Part Time over time
   - **Value:** Tracks gig economy / workforce flexibility trends

3. **Experience Demand Matrix**
   - Heatmap: industry (rows) × experience band (columns)
   - Color intensity = posting count
   - **Value:** Reveals experience gaps for training programs

4. **Labor Market Balance**
   - Horizontal bar: industries ranked by avg applications
   - Over-subscribed (high apps) vs Under-subscribed (low apps)
   - **Value:** Identifies labor shortage/surplus sectors

5. **Market Map**
   - Scatter bubble chart: x=avg salary, y=posting count, size=vacancies
   - Color = industry
   - **Value:** Holistic view of sector positioning (salary vs demand)

### Interactivity

**Filters:**
- All filters use Streamlit widgets (`selectbox`, `multiselect`, `slider`)
- Live updates via reactive rendering (no "Submit" button needed)
- Filter state resets per page (Q14 Decision)

**Tooltips:**
- Plotly charts include hover data (e.g., repost rate, avg applications)
- Metric cards have help text explaining calculation

**Drill-Downs:**
- Click industry in home page chart → filter propagates (via `st.session_state` if implemented)
- Currently: manual filter selection in sidebar

**No Data States:**
- `st.warning()` messages when filters yield empty results (Q15 Decision)
- Example: "No salary data for [Role] in [Industry] at [Seniority] level"

### Design Choices

**Layout:**
- Wide mode (`st.set_page_config(layout="wide")`) for multi-column charts
- Consistent 2-3 column layouts for KPI metrics
- Horizontal bars for long category labels (industry names)

**Chart Types:**
- **Box plots** for salary ranges (shows percentiles transparently)
- **Line charts** for time trends (clear temporal patterns)
- **Heatmaps** for 2D relationships (industry × experience, role × seniority)
- **Bubble charts** for multivariate analysis (salary × demand × vacancies)
- **Donut charts** for composition (employment types, seniority mix)

**Color Scheme:**
- **Salary:** Viridis (blue-green-yellow) for continuous scales
- **Competition:** Red-Yellow-Green for ratio intensity
- **Industry:** Plotly default palette for categorical distinction
- **Trend indicators:** Green (↑) / Red (↓) / Gray (→) for growth direction

**Readability:**
- Large metric values formatted with commas (1,044,587)
- Percentages to 1 decimal (40.3%)
- Salaries with $ symbol and thousands separator ($5,200)
- Consistent heading hierarchy (st.title → st.subheader → st.markdown)

### How Each View Supports Business Objectives

| View | Persona | Business Objective Supported | Decision Enabled |
|------|---------|------------------------------|------------------|
| Industry Comparison | Career Switcher | Evaluate transition viability | "Should I switch to [Industry]?" |
| Salary Benchmarker | Career Switcher, Talent Acquisition | Set realistic expectations | "What salary should I expect/offer?" |
| Competition Intensity | Career Switcher | Assess entry difficulty | "Which roles are easiest to break into?" |
| Hard-to-Fill Indicators | Talent Acquisition | Optimize recruitment strategy | "Do I need active sourcing or post-and-wait?" |
| Sector Growth Index | Policy Analyst | Prioritize upskilling programs | "Which sectors need workforce investment?" |
| Labor Market Balance | Policy Analyst | Identify imbalances | "Where are labor shortages/surpluses?" |

---

## 4. Challenges & Learnings

### Technical Challenges

**1. Memory Management with 1M Rows**
- **Challenge:** Loading 1M rows into Pandas DataFrame consumed 800MB+ memory
- **Solution:**
  - Explicit dtype specification in `read_csv()`
  - Category dtype for low-cardinality strings (38.6% memory reduction)
  - Parquet compression (273 MB CSV → 49 MB Bronze parquet, 82% reduction)
- **Learning:** Upfront type optimization is crucial for large datasets

**2. Multi-Industry Explosion Logic**
- **Challenge:** Postings tagged to multiple industries — how to aggregate without double-counting?
- **Decision:**
  - Explode for industry-level metrics (transparent double-counting, documented)
  - Use `primary_industry` (first in list) for company-level metrics
- **Learning:** Acceptance of double-counting with clear documentation is better than complex allocation logic

**3. Salary Outlier Detection**
- **Challenge:** Simple thresholds removed valid high salaries; no thresholds allowed $23M salaries
- **Solution:** Three-stage approach (Hard Bounds → IQR Flagging → Winsorization)
- **Learning:** Hybrid approaches (rule-based + statistical) balance robustness and transparency

### Analytical Challenges

**1. Role Family Classification Without Ground Truth**
- **Challenge:** No standardized job classification field
- **Solution:** Keyword-based matching with specificity ordering
- **Trade-off:** 32% classified as "Other" (limitation accepted)
- **Learning:** Domain-specific keyword curation (e.g., "it support" vs "it " with space) matters significantly

**2. Defining "Competition"**
- **Challenge:** Is high competition good (many applicants) or bad (hard for applicants)?
- **Decision:** Frame as "applications per vacancy" with persona-specific interpretation
  - Career Switcher: Lower = harder to get hired (good for employers)
  - Talent Acquisition: Higher = easier to fill (good for recruiters)
- **Learning:** Same metric, different framing based on user perspective

**3. Seniority Tier Consolidation**
- **Challenge:** 9 position levels too granular for actionable insights
- **Solution:** Map to 4 tiers based on domain knowledge
- **Validation:** Checked distribution to ensure no tier dominated >50%
- **Learning:** Data-driven consolidation requires balancing granularity with interpretability

### Key Learnings

**1. Medallion Architecture Benefits**
- **Bronze:** Immutable raw-like data, easy to regenerate Silver if logic changes
- **Silver:** Single source of truth for all features, no redundant transformations
- **Gold:** Dashboard-optimized aggregates, sub-second query times
- **Impact:** Changed one salary threshold → only reran Silver (30 sec) instead of full pipeline

**2. Persona-Based Design**
- **Insight:** Same data, different questions
- **Example:** "Avg salary by industry" used by:
  - Career Switcher → "Is this transition worth it financially?"
  - Talent Acquisition → "Am I offering competitively?"
  - Policy Analyst → "Which sectors have wage growth?"
- **Learning:** Design dashboards around user questions, not just data tables

**3. Parameter Tuning with Visual Feedback**
- **Approach:** Added "Parameter Tuning" section in `02_silver.ipynb` with before/after plots
- **Result:** Easy to validate salary bounds ($500-$50k) by seeing distribution
- **Learning:** EDA notebooks are not just for exploration — they're for **validation and tuning**

### Next Steps & Improvements

**Short-Term (If Continuing Project):**
1. **Skill Extraction:** Parse job descriptions for technical skills (Python, SQL, etc.)
2. **Location Analysis:** Geocode postings for geographic demand patterns
3. **Predictive Modeling:** Forecast posting volumes by industry for next quarter
4. **Dashboard Deployment:** Host on Streamlit Cloud for public access

**Long-Term:**
5. **Real-Time Updates:** Automate ETL pipeline to process new job posting data daily
6. **Company Profiling:** Deep-dive dashboards for individual companies' hiring patterns
7. **Salary Prediction:** ML model to predict competitive salary given role + experience + industry
8. **Integration:** Connect to external APIs (LinkedIn, Glassdoor) for enriched insights

---

## 5. Screenshots

*(To be added: 4 key dashboard screenshots)*

**Recommended screenshots:**
1. Home page showing market overview KPIs and persona navigator
2. Career Switcher page: Industry comparison + salary benchmarker
3. Talent Acquisition page: Salary benchmark + hard-to-fill indicators
4. Policy Analyst page: Sector growth index + market map

---

## 6. Appendix

### Pipeline Summary

```
Bronze rows:        1,044,587
Silver rows:        1,044,587
Bronze → Silver loss: 0.00%

Gold tables:
  - agg_monthly_postings:     645 rows
  - agg_salary_by_role:     2,924 rows
  - agg_industry_demand:       43 rows
  - agg_competition:          731 rows
  - agg_top_companies:  2,285,493 rows
  - agg_experience_demand:    860 rows
```

### Configuration Parameters Used

```python
SALARY_FLOOR = 500
SALARY_CEILING = 50_000
WINSOR_PERCENTILES = (0.01, 0.99)
IQR_MULTIPLIER = 1.5
MAX_EXPERIENCE_YEARS = 30
```

### Test Results

- **Total tests:** 15
- **Passed:** 15
- **Coverage:** Key transformations (seniority, salary, roles, categories)
- **Framework:** pytest

### Performance Metrics

| Stage | Runtime | Output Size |
|-------|---------|-------------|
| Bronze | 25 sec | 49 MB |
| Silver | 45 sec | 63 MB |
| Gold | 12 sec | 15 MB (total) |
| **Total ETL** | **82 sec** | **127 MB** |
| Dashboard load | 3 sec | N/A |

---

## Conclusion

This project successfully transformed 1M+ raw job postings into a multi-persona analytics platform that serves three distinct user groups with tailored insights. The Medallion architecture ensures data quality, reproducibility, and maintainability, while the persona-based dashboard design aligns features directly with business objectives.

**Key Achievements:**
- ✅ Cleaned and enriched 1M+ rows with 0% data loss (Bronze → Silver)
- ✅ Generated 6 business-ready aggregate tables (Gold layer)
- ✅ Built 3-persona dashboard with 15+ interactive visualizations
- ✅ Delivered sub-second query performance via Parquet + Streamlit caching
- ✅ Documented pipeline with reproducible notebooks and tests

**Impact:** Users can now make data-driven decisions on career transitions, recruitment strategies, and labor policy based on Singapore's actual job market dynamics (Oct 2022 - Apr 2023).

---

**🤖 Generated with Claude Code**
**Date:** 2026-02-18
**Project:** Singapore Jobs Analytics Dashboard
