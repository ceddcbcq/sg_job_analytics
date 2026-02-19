# Quick Start Guide
## Singapore Jobs Analytics Dashboard

Get up and running in 5 minutes!

---

## ✅ Prerequisites

- Python 3.9+ (tested with 3.14.2)
- Python environment requirements in requirements.txt
- 8GB+ RAM recommended
- `SGJobData.csv` in `data/raw/` directory

---

## 🚀 Option 1: Run Complete ETL Pipeline

Execute the full data pipeline (Bronze → Silver → Gold):

```bash
python -c "
from src.etl.sg_jobs_etl import SGJobsETL
etl = SGJobsETL()
etl.run_all()
etl.pipeline_summary()
"
```

**What happens:**
- ✅ Loads 1M+ rows from raw CSV
- ✅ Cleans and validates data (Bronze layer)
- ✅ Engineers features (Silver layer)
- ✅ Generates 6 business tables (Gold layer)
- ✅ Prints summary of row counts at each stage

**Time:** ~90 seconds

**Output:**
```
Bronze rows:        1,044,587
Silver rows:        1,044,587
Bronze → Silver loss: 0.00%

Gold tables: 6
  - agg_monthly_postings:     645 rows
  - agg_salary_by_role:     2,924 rows
  - agg_industry_demand:       43 rows
  - agg_competition:          731 rows
  - agg_top_companies:  2,285,493 rows
  - agg_experience_demand:    860 rows
```

---

## 🎯 Option 2: Launch Interactive Dashboard

Start the Streamlit web application:

```bash
streamlit run app/Home.py
```

**What opens:**
- Home page with market overview KPIs
- 4 interactive pages (Home + 3 personas)
- 15+ visualizations with filters
- Real-time chart updates

**Access:** http://localhost:8501

**Time to load:** <5 seconds

**Stop:** Press `Ctrl+C` in terminal

---

## 📚 Option 3: Explore in Jupyter Notebooks

Interactive analysis and EDA walkthrough:

```bash
jupyter notebook notebooks/
```

**Notebooks available:**
1. `01_bronze.ipynb` - Data quality analysis
2. `02_silver.ipynb` - Feature engineering + EDA + parameter tuning
3. `03_gold.ipynb` - Business aggregates validation

**Time:** ~10 minutes per notebook

---

## 🔧 Verify Installation

Test that everything is set up correctly:

```python
python -c "
import pandas as pd
import streamlit as st
import plotly.express as px
from src.etl.sg_jobs_etl import SGJobsETL

print('✅ All dependencies installed')
print('✅ SGJobsETL class imported successfully')

etl = SGJobsETL()
print('✅ ETL instance created')
print('✅ Ready to run!')
"
```

---

## 📊 Common Commands

### Check pipeline status
```python
from src.etl.sg_jobs_etl import SGJobsETL
etl = SGJobsETL()
summary = etl.pipeline_summary()
```

### Load specific data layer
```python
from src.etl.sg_jobs_etl import SGJobsETL
etl = SGJobsETL()

bronze_df = etl.load_bronze()  # 1,044,587 rows
silver_df = etl.load_silver()  # 1,044,587 rows
gold_df = etl.load_gold('agg_industry_demand')  # 43 rows
```

### Export Silver data to CSV
```python
import pandas as pd
df = pd.read_parquet('data/silver/sg_jobs_silver.parquet')
df.to_csv('data/silver/sg_jobs_silver.csv', index=False)
```

### Run tests
```bash
pip install pytest
pytest tests/ -v
```

---

## 🎯 Dashboard Navigation

### Home Page
- **View:** Market overview with KPIs and persona options
- **Filters:** None (summary view)
- **Use case:** Get a quick snapshot of the job market

### Career Switcher Page
- **View:** Compare industries for career transitions
- **Filters:** From Industry, To Industry, Seniority, Min Years Experience
- **Use case:** "Should I switch from IT to Finance?"

### Talent Acquisition Page
- **View:** Salary benchmarks and hard-to-fill indicators
- **Filters:** Role Family, Industry, Seniority (multi-select)
- **Use case:** "What salary should I offer for a Senior Engineer?"

### Policy Analyst Page
- **View:** Sector growth, employment trends, labor market balance
- **Filters:** Industries (multi-select), Date Range
- **Use case:** "Which sectors are growing fastest?"

---

## ⚡ Performance Tips

### Faster Dashboard Loads
- Dashboard caches all data after first load
- Filters update in real-time (no submit button needed)
- Restart Streamlit to clear cache: `Ctrl+C` → run command again

### Faster ETL Execution
- ETL takes ~90 seconds for 1M rows
- Parquet format (49-63 MB) loads 10x faster than CSV (273 MB)
- Only re-run layers you modified (Bronze if you change raw data, Silver if you change config, Gold if you change aggregation logic)

### Faster Notebook Exploration
- Notebooks use `@st.cache_data`-equivalent concepts
- Run cells in order to maintain state
- Modify parameters in config.py and re-run Silver notebook to test changes

---

## 🐛 Troubleshooting

### "FileNotFoundError: data/raw/SGJobData.csv"
**Solution:** Place the CSV file in the correct directory:
```bash
mv ~/Downloads/SGJobData.csv ./data/raw/
```

### "No data matches current filters"
**Solution:** This is a valid result, not an error. Try:
- Selecting "All" for optional filters
- Expanding date range slider
- Choosing different industry combination

### "ModuleNotFoundError: No module named X"
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### "Dashboard shows empty charts"
**Solution:** Ensure ETL pipeline has run:
```python
from src.etl.sg_jobs_etl import SGJobsETL
etl = SGJobsETL()
etl.run_all()
```

### "Out of memory during ETL"
**Solution:** Close other applications and retry. If persistent, try:
```python
# Process in smaller chunks (advanced)
etl = SGJobsETL()
bronze_df = etl.run_bronze()
# (rerun if needed)
```

---

## 📖 Next Steps

1. **For Data Analysis:**
   - Explore `02_silver.ipynb` for parameter tuning section
   - Review salary distributions to validate bounds
   - Adjust `src/etl/config.py` if needed and re-run Silver

2. **For Dashboard Use:**
   - Start with Home page to understand data scope
   - Use Career Switcher to compare 2 industries
   - Try Talent Acquisition for salary research
   - Explore Policy Analyst for sector trends

3. **For Development:**
   - Read `README.md` for complete documentation
   - Review `final_report.md` for methodology details
   - Check `implementation_plan.md` for architecture overview
   - Examine `src/etl/sg_jobs_etl.py` for code structure

4. **For Assignment Submission:**
   - Include `final_report.md` as primary deliverable
   - Add 4 dashboard screenshots
   - Provide GitHub link or zip file
   - Reference this quickstart for setup instructions

---

## 💡 Tips & Tricks

### Customize Dashboard
Edit `app/pages/*.py` to add filters, change charts, or add new visualizations. All pages use Gold tables loaded from parquet files.

### Tune Salary Parameters
1. Review diagnostics in `02_silver.ipynb` (Parameter Tuning section)
2. Edit `src/etl/config.py` (change SALARY_FLOOR, IQR_MULTIPLIER, etc.)
3. Re-run: `etl.run_silver()` (only Silver updates, ~45 sec)

### Export Cleaned Data
```python
import pandas as pd
# Export full Silver dataset
df = pd.read_parquet('data/silver/sg_jobs_silver.parquet')
df.to_csv('output.csv', index=False)

# Export subset
df[['title', 'role_family', 'average_salary_clean', 'primary_industry']].to_csv('roles.csv')
```

### Compare Industries
```python
import pandas as pd
industry_demand = pd.read_parquet('data/gold/agg_industry_demand.parquet')
industry_demand.nlargest(10, 'posting_count')[['industry', 'posting_count', 'avg_salary']]
```

---

## 🆘 Need Help?

1. **Setup Issues:** Check `README.md` Troubleshooting section
2. **Data Questions:** Review `final_report.md` for methodology
3. **Code Questions:** See inline comments in `src/etl/sg_jobs_etl.py`
4. **Dashboard Usage:** Hover tooltips on charts explain metrics

---

## ✅ You're Ready!

You now have:
- ✅ Clean, enriched data (Silver layer)
- ✅ Business-ready aggregates (Gold layer)
- ✅ Interactive dashboard (4 pages, 3 personas)
- ✅ Complete documentation

**Happy exploring! 🚀**

---

*Last updated: 2026-02-18*
*Singapore Jobs Analytics Dashboard*
