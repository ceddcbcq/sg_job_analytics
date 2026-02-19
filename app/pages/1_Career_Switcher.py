"""
Career Switcher Persona
Help mid-career professionals pivot industries
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Career Switcher", page_icon="🎯", layout="wide")

st.title("🎯 Career Switcher Analytics")
st.markdown("**Compare industries, benchmark salaries, and assess competition for your career transition**")

# Data loading
@st.cache_data
def load_industry_demand():
    return pd.read_parquet("data/gold/agg_industry_demand.parquet")

@st.cache_data
def load_salary_by_role():
    return pd.read_parquet("data/gold/agg_salary_by_role.parquet")

@st.cache_data
def load_competition():
    return pd.read_parquet("data/gold/agg_competition.parquet")

@st.cache_data
def load_experience_demand():
    return pd.read_parquet("data/gold/agg_experience_demand.parquet")

try:
    industry_demand = load_industry_demand()
    salary_by_role = load_salary_by_role()
    competition = load_competition()
    experience_demand = load_experience_demand()

    # Sidebar filters
    st.sidebar.header("🔧 Transition Parameters")

    industries = sorted(industry_demand['industry'].unique())
    from_industry = st.sidebar.selectbox("From Industry", industries, index=industries.index('Information Technology') if 'Information Technology' in industries else 0)
    to_industry = st.sidebar.selectbox("To Industry", industries, index=industries.index('Banking and Financial Services') if 'Banking and Financial Services' in industries else 1)

    seniority_options = ['Entry', 'Mid', 'Senior', 'Management']
    seniority = st.sidebar.selectbox("Your Seniority Tier", seniority_options, index=1)

    min_years_exp = st.sidebar.slider("Minimum Years Experience", 0, 15, 3)

    st.markdown("---")

    # Side-by-side industry comparison
    st.subheader("📊 Industry Comparison")

    col1, col2 = st.columns(2)

    # Get stats for both industries
    from_stats = industry_demand[industry_demand['industry'] == from_industry].iloc[0] if len(industry_demand[industry_demand['industry'] == from_industry]) > 0 else None
    to_stats = industry_demand[industry_demand['industry'] == to_industry].iloc[0] if len(industry_demand[industry_demand['industry'] == to_industry]) > 0 else None

    with col1:
        st.markdown(f"### 📍 {from_industry}")
        if from_stats is not None:
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("Total Postings", f"{int(from_stats['posting_count']):,}")
                st.metric("Avg Applications", f"{from_stats['avg_applications']:.1f}")
            with metric_col2:
                st.metric("Avg Salary", f"${from_stats['avg_salary']:,.0f}/mo")
                st.metric("Repost Rate", f"{from_stats['repost_rate']*100:.1f}%")

    with col2:
        st.markdown(f"### 🎯 {to_industry}")
        if to_stats is not None:
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("Total Postings", f"{int(to_stats['posting_count']):,}")
                st.metric("Avg Applications", f"{to_stats['avg_applications']:.1f}")
            with metric_col2:
                st.metric("Avg Salary", f"${to_stats['avg_salary']:,.0f}/mo")
                st.metric("Repost Rate", f"{to_stats['repost_rate']*100:.1f}%")

    st.markdown("---")

    # Role availability in target industry
    st.subheader(f"💼 Top Roles in {to_industry}")

    target_comp = competition[competition['industry'] == to_industry].copy()
    if len(target_comp) > 0:
        top_roles = target_comp.nlargest(15, 'posting_count').sort_values('posting_count', ascending=True)

        fig = px.bar(top_roles, x='posting_count', y='role_family', orientation='h',
                     labels={'posting_count': 'Number of Postings', 'role_family': 'Role'},
                     color='competition_ratio_median',
                     color_continuous_scale='RdYlGn_r',
                     hover_data=['avg_applications'])
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No role data available for selected industry")

    st.markdown("---")

    # Salary benchmarker
    st.subheader(f"💰 Salary Benchmark: {to_industry} - {seniority}")

    salary_filtered = salary_by_role[
        (salary_by_role['industry'] == to_industry) &
        (salary_by_role['seniority_tier'] == seniority)
    ].copy()

    if len(salary_filtered) > 0:
        salary_filtered = salary_filtered.sort_values('salary_median', ascending=True)

        fig = go.Figure()

        # Add box plot bars (p25 to p75)
        for idx, row in salary_filtered.iterrows():
            fig.add_trace(go.Box(
                y=[row['role_family']],
                q1=[row['salary_p25']],
                median=[row['salary_median']],
                q3=[row['salary_p75']],
                lowerfence=[row['salary_p25']],
                upperfence=[row['salary_p75']],
                name=row['role_family'],
                orientation='h',
                showlegend=False
            ))

        fig.update_layout(
            title=f"Salary Range by Role ({seniority} Level)",
            xaxis_title="Monthly Salary (SGD)",
            yaxis_title="Role Family",
            height=500
        )
        st.plotly_chart(fig, width="stretch")

        st.caption("📊 Boxes show 25th to 75th percentile salary range, line indicates median")
    else:
        st.warning(f"No salary data for {to_industry} at {seniority} level")

    st.markdown("---")

    # Competition heatmap
    st.subheader(f"🔥 Competition Intensity: {to_industry}")

    comp_filtered = competition[competition['industry'] == to_industry].copy()
    if len(comp_filtered) > 0:
        # Pivot for heatmap
        heatmap_data = comp_filtered.pivot_table(
            values='competition_ratio_median',
            index='role_family',
            aggfunc='mean',
            observed=True
        ).sort_values('competition_ratio_median', ascending=False).head(15).reset_index()

        fig = px.bar(heatmap_data, x='competition_ratio_median', y='role_family',
                     orientation='h',
                     labels={'competition_ratio_median': 'Median Competition Ratio (Apps/Vacancy)', 'role_family': 'Role'},
                     color='competition_ratio_median',
                     color_continuous_scale='Reds')
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, width="stretch")

        st.caption("📊 Higher ratio = more competitive (more applications per vacancy)")
    else:
        st.warning("No competition data available")

    st.markdown("---")

    # Experience demand
    st.subheader(f"📚 Experience Requirements: {to_industry}")

    exp_filtered = experience_demand[experience_demand['industry'] == to_industry].copy()
    if len(exp_filtered) > 0:
        exp_summary = exp_filtered.groupby('experience_band', observed=True).agg({'posting_count': 'sum'}).reset_index()
        exp_summary = exp_summary.sort_values('posting_count', ascending=False)

        fig = px.bar(exp_summary, x='experience_band', y='posting_count',
                     labels={'experience_band': 'Experience Band', 'posting_count': 'Number of Postings'},
                     color='posting_count',
                     color_continuous_scale='Greens')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No experience requirement data available")

    # Insights
    with st.expander("💡 Key Insights & Recommendations"):
        if from_stats is not None and to_stats is not None:
            salary_diff = ((to_stats['avg_salary'] - from_stats['avg_salary']) / from_stats['avg_salary']) * 100
            comp_diff = to_stats['avg_applications'] - from_stats['avg_applications']

            st.markdown(f"""
            **Salary Outlook:** {to_industry} offers {salary_diff:+.1f}% {'higher' if salary_diff > 0 else 'lower'} average salary

            **Competition Level:** {to_industry} has {comp_diff:+.1f} {'more' if comp_diff > 0 else 'fewer'} applications per posting on average

            **Recommended Actions:**
            1. Focus on roles with lower competition ratios for faster entry
            2. Upskill in areas matching {to_industry} demand
            3. Consider roles at your current seniority level ({seniority}) for smoother transition
            4. Network with companies in {to_industry} with active hiring
            """)

except FileNotFoundError:
    st.error("⚠️ Data files not found. Please run the ETL pipeline first.")
except Exception as e:
    st.error(f"An error occurred: {e}")
