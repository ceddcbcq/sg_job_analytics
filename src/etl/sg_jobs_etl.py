"""
Singapore Jobs ETL Pipeline
Medallion Architecture: Bronze → Silver → Gold
"""

import os
import json
import re
import pandas as pd
import numpy as np
from typing import Dict, Optional
from src.etl import config


class SGJobsETL:
    """
    Medallion Architecture ETL Pipeline for Singapore Jobs Data

    Layers:
        - Bronze: Raw data cleaning (remove synthetic, nulls, bad cols)
        - Silver: Feature engineering (categories, seniority, salary, roles)
        - Gold: Business aggregates (6 tables for dashboard)

    Usage:
        etl = SGJobsETL()
        etl.run_all()  # Run complete pipeline

        # OR step-by-step
        bronze_df = etl.run_bronze()
        silver_df = etl.run_silver()
        gold_tables = etl.run_gold()
    """

    def __init__(self, config_override: Optional[Dict] = None, strict_mode: bool = False):
        """
        Initialize ETL pipeline

        Args:
            config_override: Optional dict to override default config values
            strict_mode: If True, raise exceptions on data quality warnings
        """
        # Load config
        self.config = {
            'PATHS': config.PATHS,
            'SALARY_FLOOR': config.SALARY_FLOOR,
            'SALARY_CEILING': config.SALARY_CEILING,
            'WINSOR_PERCENTILES': config.WINSOR_PERCENTILES,
            'IQR_MULTIPLIER': config.IQR_MULTIPLIER,
            'SENIORITY_MAP': config.SENIORITY_MAP,
            'EXPERIENCE_BANDS': config.EXPERIENCE_BANDS,
            'MAX_EXPERIENCE_YEARS': config.MAX_EXPERIENCE_YEARS,
            'ROLE_KEYWORDS': config.ROLE_KEYWORDS,
            'MIN_EXPECTED_ROWS': config.MIN_EXPECTED_ROWS,
            'MAX_BRONZE_TO_SILVER_LOSS_PCT': config.MAX_BRONZE_TO_SILVER_LOSS_PCT,
        }

        # Apply overrides
        if config_override:
            self.config.update(config_override)

        self.strict_mode = strict_mode

    # ========================================================================
    # BRONZE LAYER
    # ========================================================================

    def run_bronze(self) -> pd.DataFrame:
        """
        Execute Bronze layer pipeline: Raw → Clean

        Returns:
            pd.DataFrame: Bronze layer data
        """
        print("\n" + "="*70)
        print("BRONZE LAYER: Raw Data Cleaning")
        print("="*70)

        df = self._load_raw()
        df = self._drop_synthetic_rows(df)
        df = self._drop_null_rows(df)
        df = self._drop_useless_cols(df)
        df = self._cast_dtypes(df)
        self._save_bronze(df)

        print(f"\n✅ Bronze layer complete: {len(df):,} rows")
        print("="*70 + "\n")

        return df

    def _load_raw(self) -> pd.DataFrame:
        """Load raw CSV with explicit dtypes"""
        print("[Bronze] Loading raw CSV...")

        raw_path = self.config['PATHS']['raw']

        if not os.path.exists(raw_path):
            raise FileNotFoundError(
                f"Raw data not found at: {raw_path}\n"
                f"Please place SGJobData.csv in data/raw/"
            )

        # Define dtypes for known columns
        dtype_dict = {
            'numberOfVacancies': 'Int64',  # Nullable integer
            'metadata_totalNumberJobApplication': 'Int64',
            'metadata_totalNumberOfView': 'Int64',
            'metadata_repostCount': 'Int64',
            'minimumYearsExperience': 'Int64',
            'salary_minimum': 'float64',
            'salary_maximum': 'float64',
            'average_salary': 'float64',
        }

        df = pd.read_csv(raw_path, dtype=dtype_dict, low_memory=False)

        print(f"[Bronze]   Loaded {len(df):,} rows × {len(df.columns)} columns")
        print(f"[Bronze]   File size: {os.path.getsize(raw_path) / 1024**2:.1f} MB")

        return df

    def _drop_synthetic_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove synthetic test data with dual validation

        Q1 Decision: Filter by prefix + validate with salary check
        """
        print("[Bronze] Filtering synthetic rows...")

        initial_count = len(df)
        synthetic_mask = df['metadata_jobPostId'].str.startswith('RANDOM_JOB_', na=False)
        synthetic_df = df[synthetic_mask]

        if len(synthetic_df) > 0:
            # Validation: check if these rows have anomalous salaries
            max_salary = synthetic_df[['salary_minimum', 'salary_maximum']].max().max()
            high_salary_count = (
                (synthetic_df['salary_minimum'] > 100_000) |
                (synthetic_df['salary_maximum'] > 100_000)
            ).sum()

            print(f"[Bronze]   Found {len(synthetic_df):,} RANDOM_JOB_ rows")
            print(f"[Bronze]   Max salary in filtered rows: ${max_salary:,.0f}/month")
            print(f"[Bronze]   Rows with salary >$100k: {high_salary_count:,}")

            # Safety warning if removing rows with normal salaries
            if max_salary < 20_000:
                warning_msg = (
                    f"[Bronze]   ⚠️  WARNING: RANDOM_JOB_ rows have normal salaries (<$20k)\n"
                    f"[Bronze]   ⚠️  Manual review recommended before proceeding"
                )
                print(warning_msg)
                if self.strict_mode:
                    raise ValueError("Synthetic rows validation failed - salaries appear normal")

        df_clean = df[~synthetic_mask].copy()
        removed_count = initial_count - len(df_clean)

        print(f"[Bronze]   Removed {removed_count:,} synthetic rows")

        return df_clean

    def _drop_null_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows where all object columns are null (row-wide nulls)"""
        print("[Bronze] Removing row-wide null entries...")

        initial_count = len(df)

        # Drop rows where title is null (primary indicator of row-wide nulls)
        df_clean = df[df['title'].notna()].copy()

        removed_count = initial_count - len(df_clean)
        print(f"[Bronze]   Removed {removed_count:,} null rows")

        return df_clean

    def _drop_useless_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop columns that are 100% null or constant"""
        print("[Bronze] Dropping useless columns...")

        cols_to_drop = []

        # Known useless columns from plan
        known_useless = ['occupationId', 'status_id', 'salary_type']
        for col in known_useless:
            if col in df.columns:
                cols_to_drop.append(col)

        if cols_to_drop:
            df_clean = df.drop(columns=cols_to_drop)
            print(f"[Bronze]   Dropped {len(cols_to_drop)} columns: {', '.join(cols_to_drop)}")
        else:
            df_clean = df.copy()
            print(f"[Bronze]   No useless columns found")

        return df_clean

    def _cast_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct data types for all columns"""
        print("[Bronze] Casting data types...")

        # Parse date columns
        date_cols = ['metadata_newPostingDate', 'metadata_originalPostingDate', 'metadata_expiryDate']
        parsed_count = 0
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                parsed_count += 1

        print(f"[Bronze]   Parsed {parsed_count} date columns")

        return df

    def _save_bronze(self, df: pd.DataFrame) -> None:
        """Save Bronze layer as Parquet"""
        print("[Bronze] Saving Bronze parquet...")

        bronze_path = self.config['PATHS']['bronze']
        os.makedirs(os.path.dirname(bronze_path), exist_ok=True)

        df.to_parquet(bronze_path, compression='snappy', index=False)

        file_size = os.path.getsize(bronze_path) / 1024**2
        print(f"[Bronze]   Saved to: {bronze_path}")
        print(f"[Bronze]   File size: {file_size:.1f} MB")

    # ========================================================================
    # SILVER LAYER
    # ========================================================================

    def run_silver(self) -> pd.DataFrame:
        """
        Execute Silver layer pipeline: Clean → Enriched

        Returns:
            pd.DataFrame: Silver layer data
        """
        print("\n" + "="*70)
        print("SILVER LAYER: Feature Engineering")
        print("="*70)

        df = self.load_bronze()
        df = self._parse_categories(df)
        df = self._map_seniority(df)
        df = self._clean_salary(df)
        df = self._parse_dates(df)
        df = self._extract_role_family(df)
        df = self._add_derived_features(df)
        df = self._optimize_dtypes(df)
        self._save_silver(df)

        print(f"\n✅ Silver layer complete: {len(df):,} rows")
        print("="*70 + "\n")

        return df

    def _parse_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse JSON categories into industry fields

        Creates:
        - industry_list: List of all industries (for explosion)
        - primary_industry: First industry in list (for company aggregates)
        - industry_count: Number of industries tagged to posting
        """
        print("[Silver] Parsing categories (JSON → industries)...")

        def parse_category(cat_string):
            if pd.isna(cat_string):
                return []

            try:
                # Parse JSON array of objects
                categories = json.loads(cat_string)
                # Extract "category" field from each object
                if isinstance(categories, list):
                    return [item.get('category', '') for item in categories if isinstance(item, dict)]
                return []
            except:
                # Fallback: regex extraction for category field
                matches = re.findall(r'"category":"([^"]+)"', str(cat_string))
                return matches if matches else []

        df['industry_list'] = df['categories'].apply(parse_category)
        df['primary_industry'] = df['industry_list'].apply(
            lambda x: x[0] if len(x) > 0 else 'Unknown'
        )
        df['industry_count'] = df['industry_list'].apply(len)

        unique_industries = df['primary_industry'].nunique()
        print(f"[Silver]   Parsed {unique_industries} unique industries")
        print(f"[Silver]   Avg industries per posting: {df['industry_count'].mean():.2f}")

        return df

    def _map_seniority(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map 9 position levels → 4 seniority tiers

        Q8 Decision: Use SENIORITY_MAP from config
        """
        print("[Silver] Mapping seniority levels (9 → 4 tiers)...")

        seniority_map = self.config['SENIORITY_MAP']
        df['seniority_tier'] = df['positionLevels'].map(seniority_map)

        # Fill unmapped with "Unknown"
        df['seniority_tier'] = df['seniority_tier'].fillna('Unknown')

        tier_counts = df['seniority_tier'].value_counts()
        print(f"[Silver]   Seniority distribution:")
        for tier, count in tier_counts.items():
            print(f"[Silver]     {tier}: {count:,} ({count/len(df)*100:.1f}%)")

        return df

    def _clean_salary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Three-stage salary cleaning (Q7 Decision: Option A)

        Stage 1: Hard business bounds ($500 - $50,000)
        Stage 2: IQR-based outlier flagging (preserve data)
        Stage 3: Winsorization at 1st/99th percentile
        """
        print("[Silver] Stage 1/3: Applying hard salary bounds...")

        # Preserve raw values
        df['salary_minimum_raw'] = df['salary_minimum']
        df['salary_maximum_raw'] = df['salary_maximum']

        # Stage 1: Hard bounds
        floor = self.config['SALARY_FLOOR']
        ceiling = self.config['SALARY_CEILING']

        df.loc[df['salary_minimum'] < floor, 'salary_minimum'] = np.nan
        df.loc[df['salary_maximum'] < floor, 'salary_maximum'] = np.nan
        df.loc[df['salary_minimum'] > ceiling, 'salary_minimum'] = np.nan
        df.loc[df['salary_maximum'] > ceiling, 'salary_maximum'] = np.nan

        # Fix inverted min/max
        swap_mask = (df['salary_minimum'] > df['salary_maximum']) & \
                    df['salary_minimum'].notna() & df['salary_maximum'].notna()
        df.loc[swap_mask, ['salary_minimum', 'salary_maximum']] = \
            df.loc[swap_mask, ['salary_maximum', 'salary_minimum']].values

        removed_count = df['salary_minimum'].isna().sum()
        print(f"[Silver]   Removed {removed_count:,} salaries outside [${floor} - ${ceiling:,}]")

        # Stage 2: IQR outlier flagging
        print("[Silver] Stage 2/3: Flagging IQR outliers...")

        df['average_salary_temp'] = (df['salary_minimum'] + df['salary_maximum']) / 2
        valid_salaries = df['average_salary_temp'].dropna()

        if len(valid_salaries) > 0:
            Q1 = valid_salaries.quantile(0.25)
            Q3 = valid_salaries.quantile(0.75)
            IQR = Q3 - Q1

            iqr_mult = self.config['IQR_MULTIPLIER']
            lower_fence = Q1 - iqr_mult * IQR
            upper_fence = Q3 + iqr_mult * IQR

            df['salary_outlier_iqr'] = (
                (df['average_salary_temp'] < lower_fence) |
                (df['average_salary_temp'] > upper_fence)
            )

            outlier_count = df['salary_outlier_iqr'].sum()
            print(f"[Silver]   Flagged {outlier_count:,} IQR outliers (not removed)")
            print(f"[Silver]   IQR bounds: ${lower_fence:.0f} - ${upper_fence:,.0f}")
        else:
            df['salary_outlier_iqr'] = False
            print(f"[Silver]   No valid salaries for IQR calculation")

        # Stage 3: Winsorization
        print("[Silver] Stage 3/3: Winsorizing at 1st/99th percentile...")

        if len(valid_salaries) > 0:
            p01, p99 = self.config['WINSOR_PERCENTILES']
            p01_val = valid_salaries.quantile(p01)
            p99_val = valid_salaries.quantile(p99)

            df['salary_minimum_clean'] = df['salary_minimum'].clip(lower=p01_val, upper=p99_val)
            df['salary_maximum_clean'] = df['salary_maximum'].clip(lower=p01_val, upper=p99_val)
            df['average_salary_clean'] = (df['salary_minimum_clean'] + df['salary_maximum_clean']) / 2

            print(f"[Silver]   Winsorized to [${p01_val:.0f}, ${p99_val:,.0f}]")
        else:
            df['salary_minimum_clean'] = df['salary_minimum']
            df['salary_maximum_clean'] = df['salary_maximum']
            df['average_salary_clean'] = df['average_salary_temp']
            print(f"[Silver]   No winsorization applied (no valid salaries)")

        # Drop temp column
        df = df.drop(columns=['average_salary_temp'])

        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract date-based features

        Creates:
        - posting_month: YYYY-MM period
        - posting_duration_days: Days between posting and expiry
        """
        print("[Silver] Parsing date features...")

        # Extract posting month
        df['posting_month'] = df['metadata_newPostingDate'].dt.to_period('M')

        # Calculate posting duration
        df['posting_duration_days'] = (
            df['metadata_expiryDate'] - df['metadata_newPostingDate']
        ).dt.days

        avg_duration = df['posting_duration_days'].mean()
        print(f"[Silver]   Avg posting duration: {avg_duration:.1f} days")

        # Extract year and month for convenience
        df['posting_year'] = df['metadata_newPostingDate'].dt.year
        df['posting_month_num'] = df['metadata_newPostingDate'].dt.month

        return df

    def _extract_role_family(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract role family via keyword matching

        Q8 Decision: First match wins, ROLE_KEYWORDS ordered by specificity
        """
        print("[Silver] Extracting role families from job titles...")

        def classify_role(title: str) -> str:
            if pd.isna(title):
                return "Other"

            title_lower = title.lower()

            # Iterate in order (most specific first)
            for role_family, keywords in self.config['ROLE_KEYWORDS'].items():
                for keyword in keywords:
                    if keyword in title_lower:
                        return role_family

            return "Other"

        df['role_family'] = df['title'].apply(classify_role)

        # Log distribution
        role_counts = df['role_family'].value_counts()
        print(f"[Silver]   Classified into {len(role_counts)} role families")
        print(f"[Silver]   Top 5: {', '.join(role_counts.head(5).index.tolist())}")

        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add computed features for analysis

        Creates:
        - experience_band: Binned years of experience
        - competition_ratio: Applications per vacancy
        - is_reposted: Boolean flag for reposts
        - annual_salary_clean: Monthly salary × 12
        """
        print("[Silver] Adding derived features...")

        # Experience bands
        def get_experience_band(years):
            if pd.isna(years):
                return 'Unknown'

            # Cap at max
            years = min(years, self.config['MAX_EXPERIENCE_YEARS'])

            for min_yr, max_yr, label in self.config['EXPERIENCE_BANDS']:
                if min_yr <= years <= max_yr:
                    return label

            return 'Unknown'

        df['experience_band'] = df['minimumYearsExperience'].apply(get_experience_band)

        # Competition ratio (applications per vacancy)
        df['competition_ratio'] = df['metadata_totalNumberJobApplication'] / df['numberOfVacancies'].replace(0, np.nan)

        # Repost flag
        df['is_reposted'] = df['metadata_repostCount'] > 0

        # Annual salary
        df['annual_salary_clean'] = df['average_salary_clean'] * 12

        print(f"[Silver]   Experience bands: {df['experience_band'].nunique()} unique")
        print(f"[Silver]   Avg competition ratio: {df['competition_ratio'].mean():.2f} applications/vacancy")
        print(f"[Silver]   Reposted jobs: {df['is_reposted'].sum():,} ({df['is_reposted'].mean()*100:.1f}%)")

        return df

    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert appropriate columns to memory-efficient dtypes

        Target: Reduce memory from ~800MB to ~300-400MB
        """
        print("[Silver] Optimizing data types for memory efficiency...")

        initial_memory = df.memory_usage(deep=True).sum() / 1024**2

        # Convert low-cardinality strings to category
        category_candidates = [
            'employmentTypes',
            'seniority_tier',
            'role_family',
            'experience_band',
            'primary_industry',
            'positionLevels',
            'status_jobStatus',
            'metadata_isPostedOnBehalf',
        ]

        converted_count = 0
        for col in category_candidates:
            if col in df.columns:
                unique_ratio = df[col].nunique() / len(df)
                if unique_ratio < 0.5:  # <50% unique values = good candidate
                    df[col] = df[col].astype('category')
                    converted_count += 1

        # Convert boolean flags
        if 'is_reposted' in df.columns:
            df['is_reposted'] = df['is_reposted'].astype('bool')

        final_memory = df.memory_usage(deep=True).sum() / 1024**2
        savings = (1 - final_memory / initial_memory) * 100

        print(f"[Silver]   Converted {converted_count} columns to category dtype")
        print(f"[Silver]   Memory: {initial_memory:.1f} MB → {final_memory:.1f} MB ({savings:.1f}% savings)")

        return df

    def _save_silver(self, df: pd.DataFrame) -> None:
        """Save Silver layer as Parquet"""
        print("[Silver] Saving Silver parquet...")

        silver_path = self.config['PATHS']['silver']
        os.makedirs(os.path.dirname(silver_path), exist_ok=True)

        df.to_parquet(silver_path, compression='snappy', index=False)

        file_size = os.path.getsize(silver_path) / 1024**2
        print(f"[Silver]   Saved to: {silver_path}")
        print(f"[Silver]   File size: {file_size:.1f} MB")

    # ========================================================================
    # GOLD LAYER
    # ========================================================================

    def run_gold(self) -> Dict[str, pd.DataFrame]:
        """
        Execute Gold layer pipeline: Enriched → Aggregated

        Returns:
            Dict of DataFrames (all 6 Gold tables)
        """
        print("\n" + "="*70)
        print("GOLD LAYER: Business Aggregates")
        print("="*70)

        df = self.load_silver()

        gold_tables = {}
        gold_tables['agg_monthly_postings'] = self._agg_monthly_postings(df)
        gold_tables['agg_salary_by_role'] = self._agg_salary_by_role(df)
        gold_tables['agg_industry_demand'] = self._agg_industry_demand(df)
        gold_tables['agg_competition'] = self._agg_competition(df)
        gold_tables['agg_top_companies'] = self._agg_top_companies(df)
        gold_tables['agg_experience_demand'] = self._agg_experience_demand(df)

        # Save all tables
        gold_path = self.config['PATHS']['gold']
        os.makedirs(gold_path, exist_ok=True)

        for table_name, table_df in gold_tables.items():
            output_path = os.path.join(gold_path, f"{table_name}.parquet")
            table_df.to_parquet(output_path, compression='snappy', index=False)
            print(f"[Gold]   Saved {table_name}: {len(table_df):,} rows")

        print(f"\n✅ Gold layer complete: {len(gold_tables)} tables")
        print("="*70 + "\n")

        return gold_tables

    def _agg_monthly_postings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Monthly posting trends by industry

        Grain: posting_month × primary_industry
        """
        print("[Gold] Generating agg_monthly_postings...")

        # Explode industries (Q9 Decision)
        df_exploded = df.explode('industry_list').copy()
        df_exploded = df_exploded[df_exploded['industry_list'].notna()]
        df_exploded = df_exploded.rename(columns={'industry_list': 'industry'})

        # Group by month and industry
        agg = df_exploded.groupby(['posting_month', 'industry']).agg({
            'metadata_jobPostId': 'count',
            'average_salary_clean': 'mean',
            'numberOfVacancies': 'sum',
        }).reset_index()

        agg.columns = ['posting_month', 'industry', 'posting_count', 'avg_salary', 'total_vacancies']

        # Add employment type percentages (Q11 Decision: separate columns)
        emp_type_agg = df_exploded.groupby(['posting_month', 'industry', 'employmentTypes']).size().unstack(fill_value=0)
        emp_type_pct = emp_type_agg.div(emp_type_agg.sum(axis=1), axis=0)

        # Merge employment type percentages
        for col in emp_type_pct.columns:
            col_name = f"pct_{col.lower().replace(' ', '_').replace('/', '_')}"
            emp_type_pct_reset = emp_type_pct[[col]].reset_index()
            emp_type_pct_reset.columns = ['posting_month', 'industry', col_name]
            agg = agg.merge(emp_type_pct_reset, on=['posting_month', 'industry'], how='left')

        return agg

    def _agg_salary_by_role(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Salary benchmarks by role, seniority, and industry

        Grain: role_family × seniority_tier × primary_industry
        """
        print("[Gold] Generating agg_salary_by_role...")

        # Filter rows with valid salary
        df_salary = df[df['average_salary_clean'].notna()].copy()

        # Group by role, seniority, industry
        agg = df_salary.groupby(['role_family', 'seniority_tier', 'primary_industry']).agg({
            'average_salary_clean': ['count', 'mean', lambda x: x.quantile(0.25),
                                     'median', lambda x: x.quantile(0.75)]
        }).reset_index()

        agg.columns = ['role_family', 'seniority_tier', 'industry',
                       'n', 'salary_mean', 'salary_p25', 'salary_median', 'salary_p75']

        return agg

    def _agg_industry_demand(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Industry-level KPIs

        Grain: industry (exploded)
        """
        print("[Gold] Generating agg_industry_demand...")

        # Explode industries
        df_exploded = df.explode('industry_list').copy()
        df_exploded = df_exploded[df_exploded['industry_list'].notna()]
        df_exploded = df_exploded.rename(columns={'industry_list': 'industry'})

        # Aggregate by industry
        agg = df_exploded.groupby('industry').agg({
            'metadata_jobPostId': 'count',
            'numberOfVacancies': 'sum',
            'metadata_totalNumberJobApplication': 'mean',
            'metadata_totalNumberOfView': 'mean',
            'average_salary_clean': 'mean',
            'is_reposted': 'mean',
        }).reset_index()

        agg.columns = ['industry', 'posting_count', 'total_vacancies',
                       'avg_applications', 'avg_views', 'avg_salary', 'repost_rate']

        return agg

    def _agg_competition(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Competition metrics by industry and role

        Grain: industry × role_family
        """
        print("[Gold] Generating agg_competition...")

        # Explode industries
        df_exploded = df.explode('industry_list').copy()
        df_exploded = df_exploded[df_exploded['industry_list'].notna()]
        df_exploded = df_exploded.rename(columns={'industry_list': 'industry'})

        # Filter rows with valid competition ratio
        df_comp = df_exploded[df_exploded['competition_ratio'].notna()].copy()

        # Aggregate by industry and role
        agg = df_comp.groupby(['industry', 'role_family']).agg({
            'metadata_jobPostId': 'count',
            'metadata_totalNumberJobApplication': 'mean',
            'competition_ratio': ['median', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]
        }).reset_index()

        agg.columns = ['industry', 'role_family', 'posting_count', 'avg_applications',
                       'competition_ratio_median', 'competition_ratio_p25', 'competition_ratio_p75']

        return agg

    def _agg_top_companies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Company hiring activity

        Grain: company × primary_industry (not exploded to avoid double-counting)
        """
        print("[Gold] Generating agg_top_companies...")

        # Use primary_industry only (Q9 Decision)
        agg = df.groupby(['postedCompany_name', 'primary_industry']).agg({
            'metadata_jobPostId': 'count',
            'average_salary_clean': 'mean',
            'is_reposted': 'mean',
            'numberOfVacancies': 'mean',
        }).reset_index()

        agg.columns = ['company', 'primary_industry', 'posting_count',
                       'avg_salary', 'repost_rate', 'avg_vacancies_per_post']

        return agg

    def _agg_experience_demand(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Experience requirements by industry and seniority

        Grain: industry × experience_band × seniority_tier
        """
        print("[Gold] Generating agg_experience_demand...")

        # Explode industries
        df_exploded = df.explode('industry_list').copy()
        df_exploded = df_exploded[df_exploded['industry_list'].notna()]
        df_exploded = df_exploded.rename(columns={'industry_list': 'industry'})

        # Aggregate
        agg = df_exploded.groupby(['industry', 'experience_band', 'seniority_tier']).agg({
            'metadata_jobPostId': 'count',
            'average_salary_clean': 'mean',
        }).reset_index()

        agg.columns = ['industry', 'experience_band', 'seniority_tier',
                       'posting_count', 'avg_salary']

        return agg

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def load_bronze(self) -> pd.DataFrame:
        """Load Bronze layer data"""
        bronze_path = self.config['PATHS']['bronze']
        if not os.path.exists(bronze_path):
            raise FileNotFoundError(f"Bronze data not found. Run run_bronze() first.")
        return pd.read_parquet(bronze_path)

    def load_silver(self) -> pd.DataFrame:
        """Load Silver layer data"""
        silver_path = self.config['PATHS']['silver']
        if not os.path.exists(silver_path):
            raise FileNotFoundError(f"Silver data not found. Run run_silver() first.")
        return pd.read_parquet(silver_path)

    def load_gold(self, table: str) -> pd.DataFrame:
        """
        Load specific Gold table

        Args:
            table: Table name (e.g., 'agg_monthly_postings')
        """
        gold_path = os.path.join(self.config['PATHS']['gold'], f"{table}.parquet")
        if not os.path.exists(gold_path):
            raise FileNotFoundError(f"Gold table '{table}' not found. Run run_gold() first.")
        return pd.read_parquet(gold_path)

    def pipeline_summary(self) -> Dict:
        """
        Row count summary at each layer with data quality warnings

        Q3 Decision: Log warnings if unexpected row loss
        """
        summary = {
            'bronze': 0,
            'silver': 0,
            'gold': {},
        }

        # Count rows in each layer
        bronze_path = self.config['PATHS']['bronze']
        if os.path.exists(bronze_path):
            summary['bronze'] = len(pd.read_parquet(bronze_path))

        silver_path = self.config['PATHS']['silver']
        if os.path.exists(silver_path):
            summary['silver'] = len(pd.read_parquet(silver_path))

        # Count Gold tables
        gold_dir = self.config['PATHS']['gold']
        if os.path.exists(gold_dir):
            for file in os.listdir(gold_dir):
                if file.endswith('.parquet'):
                    table_name = file.replace('.parquet', '')
                    table_path = os.path.join(gold_dir, file)
                    summary['gold'][table_name] = len(pd.read_parquet(table_path))

        # Data quality checks
        print("\n" + "="*70)
        print("PIPELINE SUMMARY")
        print("="*70)
        print(f"Bronze rows: {summary['bronze']:,}")
        print(f"Silver rows: {summary['silver']:,}")
        print(f"Gold tables: {len(summary['gold'])}")

        if summary['bronze'] > 0:
            if summary['bronze'] < self.config['MIN_EXPECTED_ROWS']:
                print(f"\n⚠️  WARNING: Bronze has only {summary['bronze']:,} rows "
                      f"(expected ≥{self.config['MIN_EXPECTED_ROWS']:,})")

            if summary['silver'] > 0:
                loss_pct = 1 - (summary['silver'] / summary['bronze'])
                print(f"Bronze → Silver loss: {loss_pct:.2%}")

                if loss_pct > self.config['MAX_BRONZE_TO_SILVER_LOSS_PCT']:
                    print(f"⚠️  WARNING: Lost {loss_pct:.1%} of rows from Bronze to Silver "
                          f"(threshold: {self.config['MAX_BRONZE_TO_SILVER_LOSS_PCT']:.1%})")

        if summary['gold']:
            print("\nGold tables:")
            for table, count in summary['gold'].items():
                print(f"  - {table}: {count:,} rows")
                if count == 0:
                    print(f"    ⚠️  WARNING: Table is empty")

        print("="*70 + "\n")

        return summary

    def run_all(self) -> None:
        """Execute complete pipeline: Bronze → Silver → Gold"""
        print("\n" + "="*70)
        print("FULL PIPELINE EXECUTION")
        print("="*70 + "\n")

        self.run_bronze()
        self.run_silver()
        self.run_gold()

        self.pipeline_summary()
