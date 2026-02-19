"""
Talent Acquisition Persona
Benchmark salaries and assess market competition for recruitment
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Talent Acquisition", page_icon="💼", layout="wide")

st.title("💼 Talent Acquisition Analytics")
st.markdown("**Market salary benchmarks, hard-to-fill roles, and hiring company intelligence**")

# Data loading
@st.cache_data
def load_salary_by_role():
    return pd.read_parquet("data/gold/agg_salary_by_role.parquet")

@st.cache_data
def load_top_companies():
    return pd.read_parquet("data/gold/agg_top_companies.parquet")

@st.cache_data
def load_competition():
    return pd.read_parquet("data/gold/agg_competition.parquet")

@st.cache_data
def load_monthly_postings():
    df = pd.read_parquet("data/gold/agg_monthly_postings.parquet")
    df['posting_month'] = df['posting_month'].astype(str)
    return df

try:
    salary_by_role = load_salary_by_role()
    top_companies = load_top_companies()
    competition = load_competition()
    monthly_postings = load_monthly_postings()

    # Sidebar filters
    st.sidebar.header("🔧 Recruitment Parameters")

    role_families = sorted(salary_by_role['role_family'].unique())
    selected_role = st.sidebar.selectbox("Role Family", role_families,
                                         index=role_families.index('Analyst') if 'Analyst' in role_families else 0)

    industries = sorted(salary_by_role['industry'].unique())
    industries_with_all = ['All'] + industries
    selected_industry = st.sidebar.selectbox("Industry", industries_with_all, index=0)

    seniority_options = sorted(salary_by_role['seniority_tier'].unique())
    selected_seniorities = st.sidebar.multiselect("Seniority Tiers", seniority_options,
                                                   default=seniority_options)

    st.markdown("---")

    # Market salary benchmark
    st.subheader(f"💰 Market Salary Benchmark: {selected_role}")

    # Filter salary data
    if selected_industry == 'All':
        salary_filtered = salary_by_role[
            (salary_by_role['role_family'] == selected_role) &
            (salary_by_role['seniority_tier'].isin(selected_seniorities))
        ].copy()
    else:
        salary_filtered = salary_by_role[
            (salary_by_role['role_family'] == selected_role) &
            (salary_by_role['industry'] == selected_industry) &
            (salary_by_role['seniority_tier'].isin(selected_seniorities))
        ].copy()

    if len(salary_filtered) > 0:
        # Aggregate by seniority
        salary_agg = salary_filtered.groupby('seniority_tier', observed=True).agg({
            'salary_median': 'median',
            'salary_p25': 'median',
            'salary_p75': 'median',
            'n': 'sum'
        }).reset_index()

        salary_agg = salary_agg.sort_values('salary_median')

        fig = go.Figure()

        for idx, row in salary_agg.iterrows():
            fig.add_trace(go.Box(
                y=[row['seniority_tier']],
                q1=[row['salary_p25']],
                median=[row['salary_median']],
                q3=[row['salary_p75']],
                lowerfence=[row['salary_p25']],
                upperfence=[row['salary_p75']],
                name=row['seniority_tier'],
                orientation='h',
                showlegend=False,
                marker_color='steelblue'
            ))

        fig.update_layout(
            title=f"Salary Range: {selected_role} by Seniority" + (f" in {selected_industry}" if selected_industry != 'All' else ""),
            xaxis_title="Monthly Salary (SGD)",
            yaxis_title="Seniority Tier",
            height=400
        )
        st.plotly_chart(fig, width="stretch")

        st.caption("📊 Boxes show market salary range (25th-75th percentile)")

        # Optional: user's current salary input
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            user_salary = st.number_input("Your Offer Salary (optional)", min_value=0, max_value=50000, value=0, step=500)
            if user_salary > 0:
                market_median = salary_agg['salary_median'].median()
                diff_pct = ((user_salary - market_median) / market_median) * 100
                if diff_pct > 0:
                    st.success(f"✅ Your offer is {diff_pct:.1f}% above market median")
                else:
                    st.warning(f"⚠️ Your offer is {abs(diff_pct):.1f}% below market median")
    else:
        st.warning(f"No salary data for {selected_role}" + (f" in {selected_industry}" if selected_industry != 'All' else ""))

    st.markdown("---")

    # Top hiring companies
    st.subheader(f"🏢 Top Hiring Companies: {selected_role}")

    # Filter companies by role (need to join with competition data)
    role_industries = competition[competition['role_family'] == selected_role]['industry'].unique()

    if len(role_industries) > 0:
        if selected_industry != 'All':
            companies_filtered = top_companies[top_companies['primary_industry'] == selected_industry].copy()
        else:
            companies_filtered = top_companies[top_companies['primary_industry'].isin(role_industries)].copy()

        # Filter companies with at least 5 postings (Q13 Decision)
        companies_filtered = companies_filtered[companies_filtered['posting_count'] >= 5]

        if len(companies_filtered) > 0:
            top15 = companies_filtered.nlargest(15, 'posting_count').sort_values('posting_count', ascending=True)

            fig = px.bar(top15, x='posting_count', y='company', orientation='h',
                         color='avg_salary',
                         labels={'posting_count': 'Number of Postings', 'company': 'Company', 'avg_salary': 'Avg Salary'},
                         color_continuous_scale='Viridis',
                         hover_data=['repost_rate'])
            fig.update_layout(height=600)
            st.plotly_chart(fig, width="stretch")

            st.caption("📊 Color intensity indicates average salary offered")
        else:
            st.warning("No companies with 5+ postings found")
    else:
        st.warning(f"No company data for {selected_role}")

    st.markdown("---")

    # Hard-to-fill indicators
    st.subheader(f"🎯 Hard-to-Fill Indicators: {selected_role}")

    # Filter competition data
    if selected_industry == 'All':
        comp_filtered = competition[competition['role_family'] == selected_role].copy()
    else:
        comp_filtered = competition[
            (competition['role_family'] == selected_role) &
            (competition['industry'] == selected_industry)
        ].copy()

    if len(comp_filtered) > 0:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_comp = comp_filtered['competition_ratio_median'].mean()
            st.metric("Avg Competition Ratio", f"{avg_comp:.2f}",
                     help="Applications per vacancy - higher = easier to fill")

        with col2:
            # Repost rate from companies data
            if selected_industry != 'All':
                repost_rate = top_companies[top_companies['primary_industry'] == selected_industry]['repost_rate'].mean()
            else:
                repost_rate = top_companies['repost_rate'].mean()
            st.metric("Market Repost Rate", f"{repost_rate*100:.1f}%",
                     help="% of jobs that were reposted - higher = harder to fill")

        with col3:
            avg_apps = comp_filtered['avg_applications'].mean()
            st.metric("Avg Applications", f"{avg_apps:.0f}",
                     help="Average applications per posting")

        with col4:
            # Posting count as demand indicator
            total_postings = comp_filtered['posting_count'].sum()
            st.metric("Market Demand", f"{total_postings:,}",
                     help="Total postings for this role")

        # Interpretation
        if avg_comp > 2:
            st.info("✅ This role typically receives good candidate flow (competition ratio > 2)")
        else:
            st.warning("⚠️ This role may be harder to fill (low competition ratio)")

    else:
        st.warning("No competition data available")

    st.markdown("---")

    # Posting velocity trend
    st.subheader(f"📈 Posting Velocity: {selected_role}")

    # Get industries for this role
    if selected_industry == 'All':
        role_industries_monthly = competition[competition['role_family'] == selected_role]['industry'].unique()
        monthly_filtered = monthly_postings[monthly_postings['industry'].isin(role_industries_monthly)].copy()
    else:
        monthly_filtered = monthly_postings[monthly_postings['industry'] == selected_industry].copy()

    if len(monthly_filtered) > 0:
        monthly_trend = monthly_filtered.groupby('posting_month').agg({'posting_count': 'sum'}).reset_index()

        fig = px.line(monthly_trend, x='posting_month', y='posting_count',
                      labels={'posting_month': 'Month', 'posting_count': 'Number of Postings'},
                      markers=True)
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch")

        # Trend analysis
        if len(monthly_trend) >= 2:
            recent = monthly_trend.iloc[-3:]['posting_count'].mean()
            older = monthly_trend.iloc[:3]['posting_count'].mean()
            trend_pct = ((recent - older) / older) * 100

            if trend_pct > 10:
                st.success(f"📈 Posting volume increasing ({trend_pct:+.1f}% recent vs earlier months)")
            elif trend_pct < -10:
                st.warning(f"📉 Posting volume decreasing ({trend_pct:+.1f}% recent vs earlier months)")
            else:
                st.info(f"➡️ Posting volume stable ({trend_pct:+.1f}% change)")
    else:
        st.warning("No monthly trend data available")

    st.markdown("---")

    # Seniority mix
    st.subheader(f"👥 Seniority Mix: {selected_role}")

    if len(salary_filtered) > 0:
        seniority_dist = salary_filtered.groupby('seniority_tier', observed=True).agg({'n': 'sum'}).reset_index()

        fig = px.pie(seniority_dist, values='n', names='seniority_tier',
                     title=f"What seniority is the market hiring?",
                     hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No seniority distribution data")

    # Recommendations
    with st.expander("💡 Recruitment Recommendations"):
        if len(comp_filtered) > 0:
            avg_comp = comp_filtered['competition_ratio_median'].mean()
            avg_salary = salary_filtered['salary_median'].mean() if len(salary_filtered) > 0 else 0

            st.markdown(f"""
            **Salary Strategy:**
            - Market median: ${avg_salary:,.0f}/month
            - Recommend offering 75th percentile (${salary_filtered['salary_p75'].mean():,.0f}) for faster fills

            **Sourcing Strategy:**
            - Competition ratio: {avg_comp:.2f} applications/vacancy
            - {'Active sourcing recommended (low competition)' if avg_comp < 2 else 'Post-and-wait viable (good competition)'}

            **Timing:**
            - Review posting velocity trends above
            - Adjust recruitment timeline based on market activity

            **Key Actions:**
            1. Benchmark your offer against market data
            2. Monitor top hiring companies for talent poaching opportunities
            3. Adjust requirements if competition ratio is too low
            """)

except FileNotFoundError:
    st.error("⚠️ Data files not found. Please run the ETL pipeline first.")
except Exception as e:
    st.error(f"An error occurred: {e}")
