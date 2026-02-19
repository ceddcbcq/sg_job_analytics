"""
Policy Analyst Persona
Macro labor market health for policy and upskilling decisions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Policy Analyst", page_icon="📈", layout="wide")

st.title("📈 Policy Analyst Dashboard")
st.markdown("**Macro labor market trends, sector growth, and employment dynamics**")

# Data loading
@st.cache_data
def load_monthly_postings():
    df = pd.read_parquet("data/gold/agg_monthly_postings.parquet")
    df['posting_month'] = df['posting_month'].astype(str)
    return df

@st.cache_data
def load_industry_demand():
    return pd.read_parquet("data/gold/agg_industry_demand.parquet")

@st.cache_data
def load_experience_demand():
    return pd.read_parquet("data/gold/agg_experience_demand.parquet")

@st.cache_data
def load_competition():
    return pd.read_parquet("data/gold/agg_competition.parquet")

try:
    monthly_postings = load_monthly_postings()
    industry_demand = load_industry_demand()
    experience_demand = load_experience_demand()
    competition = load_competition()

    # Sidebar filters
    st.sidebar.header("🔧 Analysis Parameters")

    all_industries = sorted(monthly_postings['industry'].unique())
    default_industries = all_industries[:10] if len(all_industries) > 10 else all_industries
    selected_industries = st.sidebar.multiselect("Industries", all_industries, default=[])
    heatmap_industries = selected_industries  # empty = show all 43 in heatmap
    if not selected_industries:
        selected_industries = default_industries

    # Date range
    all_months = sorted(monthly_postings['posting_month'].unique())
    date_range = st.sidebar.select_slider("Date Range", options=all_months,
                                          value=(all_months[0], all_months[-1]))

    st.markdown("---")

    # Sector growth index
    st.subheader("📊 Sector Growth Index")
    st.caption("Posting volume indexed to first month = 100")

    if len(selected_industries) > 0:
        # Filter data
        monthly_filtered = monthly_postings[
            (monthly_postings['industry'].isin(selected_industries)) &
            (monthly_postings['posting_month'] >= date_range[0]) &
            (monthly_postings['posting_month'] <= date_range[1])
        ].copy()

        if len(monthly_filtered) > 0:
            # Calculate index for each industry
            indexed_data = []
            for industry in selected_industries:
                ind_data = monthly_filtered[monthly_filtered['industry'] == industry].sort_values('posting_month')
                if len(ind_data) > 0:
                    baseline = ind_data.iloc[0]['posting_count']
                    if baseline > 0:
                        ind_data['index'] = (ind_data['posting_count'] / baseline) * 100
                        indexed_data.append(ind_data[['posting_month', 'industry', 'index']])

            if indexed_data:
                indexed_df = pd.concat(indexed_data, ignore_index=True)

                fig = px.line(indexed_df, x='posting_month', y='index', color='industry',
                              labels={'posting_month': 'Month', 'index': 'Growth Index (Base=100)', 'industry': 'Industry'},
                              markers=True)
                fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Baseline")
                fig.update_layout(height=500)
                st.plotly_chart(fig, width="stretch")

                st.caption("📊 Values above 100 indicate growth, below 100 indicate decline from first month")
            else:
                st.warning("No data available for selected industries and date range")
    else:
        st.info("Please select at least one industry from the sidebar")

    st.markdown("---")

    # Employment type shift
    st.subheader("📋 Employment Type Dynamics")

    if len(selected_industries) > 0:
        monthly_filtered = monthly_postings[
            (monthly_postings['industry'].isin(selected_industries)) &
            (monthly_postings['posting_month'] >= date_range[0]) &
            (monthly_postings['posting_month'] <= date_range[1])
        ].copy()

        # Get employment type columns
        emp_cols = [col for col in monthly_filtered.columns if col.startswith('pct_')]

        if emp_cols:
            # Aggregate employment types across selected industries
            emp_trend = monthly_filtered.groupby('posting_month')[emp_cols].mean().reset_index()

            # Reshape for stacked area chart
            emp_melted = emp_trend.melt(id_vars='posting_month', value_vars=emp_cols,
                                        var_name='employment_type', value_name='percentage')
            emp_melted['employment_type'] = emp_melted['employment_type'].str.replace('pct_', '').str.replace('_', ' ').str.title()

            fig = px.area(emp_melted, x='posting_month', y='percentage', color='employment_type',
                          labels={'posting_month': 'Month', 'percentage': 'Share (%)', 'employment_type': 'Employment Type'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")

            st.caption("📊 Stacked area shows employment type composition over time")
        else:
            st.warning("No employment type data available")

    st.markdown("---")

    # Experience demand heatmap
    st.subheader("🎓 Experience Demand Matrix")

    exp_source = experience_demand if not heatmap_industries else experience_demand[experience_demand['industry'].isin(heatmap_industries)]
    exp_pivot = exp_source.pivot_table(
        values='posting_count',
        index='industry',
        columns='experience_band',
        aggfunc='sum',
        fill_value=0,
        observed=True
    )

    # Order experience bands
    exp_order = ['0-1 yr', '2-3 yrs', '4-5 yrs', '6-10 yrs', '10+ yrs', 'Unknown']
    exp_cols = [col for col in exp_order if col in exp_pivot.columns]
    exp_pivot = exp_pivot[exp_cols]

    fig = px.imshow(exp_pivot, labels=dict(x="Experience Band", y="Industry", color="Posting Count"),
                    color_continuous_scale='YlOrRd',
                    aspect="auto")
    fig.update_layout(height=900)
    st.plotly_chart(fig, width="stretch")

    st.caption("📊 Darker colors indicate higher demand for that experience level")

    st.markdown("---")

    # Vacancy-application gap
    st.subheader("⚖️ Labor Market Balance")
    st.caption("Industries ranked by competition ratio (over/under-subscribed)")

    # Use industry demand data
    demand_filtered = industry_demand[industry_demand['industry'].isin(selected_industries)].copy() if selected_industries else industry_demand.copy()

    if len(demand_filtered) > 0:
        # Calculate supply-demand indicator (using avg_applications as proxy)
        # Higher applications = over-subscribed, lower = under-subscribed
        demand_filtered = demand_filtered.sort_values('avg_applications', ascending=True)

        # Create color coding
        median_apps = demand_filtered['avg_applications'].median()
        demand_filtered['balance'] = demand_filtered['avg_applications'].apply(
            lambda x: 'Over-subscribed' if x > median_apps else 'Under-subscribed'
        )

        fig = px.bar(demand_filtered, x='avg_applications', y='industry', orientation='h',
                     color='balance',
                     labels={'avg_applications': 'Avg Applications per Posting', 'industry': 'Industry'},
                     color_discrete_map={'Over-subscribed': 'coral', 'Under-subscribed': 'lightblue'})
        fig.add_vline(x=median_apps, line_dash="dash", line_color="red",
                      annotation_text=f"Median: {median_apps:.1f}")
        fig.update_layout(height=600)
        st.plotly_chart(fig, width="stretch")

        st.caption("📊 Industries above median may indicate surplus labor; below median may indicate shortage")

        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            total_postings = demand_filtered['posting_count'].sum()
            st.metric("Total Postings", f"{int(total_postings):,}")
        with col2:
            total_vacancies = demand_filtered['total_vacancies'].sum()
            st.metric("Total Vacancies", f"{int(total_vacancies):,}")
        with col3:
            avg_apps = demand_filtered['avg_applications'].mean()
            st.metric("Avg Applications", f"{avg_apps:.1f}")

    st.markdown("---")

    # Market map (bubble chart)
    st.subheader("🗺️ Market Map: Salary vs Demand")

    if len(selected_industries) > 0:
        map_data = industry_demand[industry_demand['industry'].isin(selected_industries)].copy()

        if len(map_data) > 0:
            fig = px.scatter(map_data, x='avg_salary', y='posting_count',
                             size='total_vacancies', color='industry',
                             hover_data=['repost_rate', 'avg_applications'],
                             labels={'avg_salary': 'Avg Salary (SGD/month)',
                                    'posting_count': 'Number of Postings',
                                    'total_vacancies': 'Total Vacancies'},
                             size_max=60)
            fig.update_layout(height=600)
            st.plotly_chart(fig, width="stretch")

            st.caption("📊 Bubble size = total vacancies; hover for repost rate and applications")
        else:
            st.warning("No data for market map")

    # Policy insights
    with st.expander("💡 Policy Insights & Recommendations"):
        if len(demand_filtered) > 0:
            # Identify fastest growing sectors
            if len(monthly_filtered) > 0:
                growth_by_industry = monthly_filtered.groupby('industry').apply(
                    lambda x: (x.iloc[-1]['posting_count'] - x.iloc[0]['posting_count']) / x.iloc[0]['posting_count'] * 100
                    if len(x) >= 2 and x.iloc[0]['posting_count'] > 0 else 0,
                    include_groups=False
                ).reset_index()
                growth_by_industry.columns = ['industry', 'growth_pct']
                top_growth = growth_by_industry.nlargest(3, 'growth_pct')

                st.markdown("**Growing Sectors:**")
                for idx, row in top_growth.iterrows():
                    st.markdown(f"- {row['industry']}: {row['growth_pct']:+.1f}% growth")

            # Identify underserved sectors (low competition)
            underserved = demand_filtered.nsmallest(3, 'avg_applications')
            st.markdown("\n**Potentially Underserved Sectors (Low Application Rates):**")
            for idx, row in underserved.iterrows():
                st.markdown(f"- {row['industry']}: {row['avg_applications']:.1f} avg applications")

            st.markdown("""
            \n**Recommended Policy Actions:**
            1. **Upskilling Programs:** Focus on high-growth sectors identified above
            2. **Labor Mobility:** Facilitate transitions from over-subscribed to under-subscribed sectors
            3. **Salary Benchmarking:** Monitor salary trends for wage policy guidance
            4. **Experience Gap:** Address mismatches in experience requirements vs supply
            """)

    st.markdown("---")
    st.caption("📊 **Data Note:** Industries are exploded - postings may count across multiple categories")
    st.caption("🤖 Generated with Claude Code | Data: Singapore Jobs Oct 2022 - Apr 2023")

except FileNotFoundError:
    st.error("⚠️ Data files not found. Please run the ETL pipeline first.")
except Exception as e:
    st.error(f"An error occurred: {e}")
