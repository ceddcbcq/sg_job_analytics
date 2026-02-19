"""
Singapore Jobs Analytics Dashboard
Home Page - Market Overview
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Page config
st.set_page_config(
    page_title="SG Jobs Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Title
st.title("🇸🇬 Singapore Jobs Market Analytics")
st.markdown("**Oct 2022 – Apr 2023** | 1M+ Job Postings")

# Data loading functions
@st.cache_data
def load_industry_demand():
    return pd.read_parquet("data/gold/agg_industry_demand.parquet")

@st.cache_data
def load_monthly_postings():
    df = pd.read_parquet("data/gold/agg_monthly_postings.parquet")
    df['posting_month'] = df['posting_month'].astype(str)
    return df

@st.cache_data
def load_kpi_metrics():
    """Read only the vacancies column from Silver — avoids industry-explosion inflation."""
    df = pd.read_parquet("data/silver/sg_jobs_silver.parquet", columns=['numberOfVacancies'])
    return len(df), int(df['numberOfVacancies'].sum())

@st.cache_data
def load_silver_sample():
    """Load sample of Silver for employment type analysis"""
    df = pd.read_parquet("data/silver/sg_jobs_silver.parquet")
    return df[['employmentTypes', 'metadata_jobPostId']].head(50000)

# Load data
try:
    industry_demand = load_industry_demand()
    monthly_postings = load_monthly_postings()
    silver_sample = load_silver_sample()
    total_postings, total_vacancies = load_kpi_metrics()

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Postings", f"{total_postings:,}")

    with col2:
        st.metric("Total Vacancies", f"{total_vacancies:,}")

    with col3:
        unique_industries = len(industry_demand)
        st.metric("Unique Industries", unique_industries)

    with col4:
        st.metric("Date Range", "Oct 2022 - Apr 2023")

    st.markdown("---")

    # Charts Row 1
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📊 Top 10 Industries by Posting Count")
        top10 = industry_demand.nlargest(10, 'posting_count').sort_values('posting_count', ascending=True)
        fig = px.bar(top10, x='posting_count', y='industry', orientation='h',
                     labels={'posting_count': 'Number of Postings', 'industry': 'Industry'},
                     color='posting_count', color_continuous_scale='Blues')
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("📋 Employment Type Breakdown")
        emp_type_counts = silver_sample['employmentTypes'].value_counts().head(5)
        fig = px.pie(values=emp_type_counts.values, names=emp_type_counts.index,
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, width="stretch")

    # Charts Row 2
    st.subheader("📈 Monthly Posting Trends")

    # Aggregate monthly totals across all industries
    monthly_totals = monthly_postings.groupby('posting_month').agg({
        'posting_count': 'sum'
    }).reset_index()

    fig = px.line(monthly_totals, x='posting_month', y='posting_count',
                  labels={'posting_month': 'Month', 'posting_count': 'Total Postings'},
                  markers=True)
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")

    # Persona Navigator
    st.subheader("📌 Explore by Persona")
    st.markdown("Choose your analytics journey based on your role:")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🎯 Career Switcher")
        st.markdown("""
        **For:** Professionals exploring new industries

        **Features:**
        - Compare industries side-by-side
        - Salary benchmarking by role & seniority
        - Competition analysis
        - Experience requirements
        """)
        st.page_link("pages/1_Career_Switcher.py", label="Explore Career Paths →", icon="🔍")

    with col2:
        st.markdown("### 💼 Talent Acquisition")
        st.markdown("""
        **For:** HR teams & recruiters

        **Features:**
        - Market salary benchmarks by role
        - Top hiring companies
        - Hard-to-fill role indicators
        - Posting velocity trends
        """)
        st.page_link("pages/2_Talent_Acquisition.py", label="Analyze Talent Market →", icon="📊")

    with col3:
        st.markdown("### 📈 Policy Analyst")
        st.markdown("""
        **For:** Government agencies & researchers

        **Features:**
        - Sector growth indices
        - Employment type shifts
        - Vacancy-application gaps
        - Labor market macro trends
        """)
        st.page_link("pages/3_Policy_Analyst.py", label="View Policy Insights →", icon="🏛️")

    st.markdown("---")
    st.caption("💡 **Note:** Total Postings & Vacancies are sourced from Silver (unique postings). Industry charts use the Gold layer where postings are exploded per industry (avg 1.69 industries/posting), so chart totals will exceed the headline counts.")
    st.caption("🤖 Generated with Claude Code | Data: Singapore Jobs Oct 2022 - Apr 2023")

except FileNotFoundError as e:
    st.error(f"""
    ⚠️ **Data files not found!**

    Please run the ETL pipeline first:

    ```python
    from src.etl.sg_jobs_etl import SGJobsETL
    etl = SGJobsETL()
    etl.run_all()
    ```

    Error: {e}
    """)
except Exception as e:
    st.error(f"An error occurred: {e}")
