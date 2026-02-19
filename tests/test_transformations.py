"""
Unit tests for SGJobsETL transformations
"""

import pytest
import pandas as pd
import numpy as np
from src.etl.sg_jobs_etl import SGJobsETL
from src.etl.config import SENIORITY_MAP, ROLE_KEYWORDS


class TestSeniorityMapping:
    """Tests for seniority tier mapping"""

    def test_all_levels_mapped(self):
        """Verify all 9 position levels map to 4 tiers"""
        assert len(SENIORITY_MAP) == 9, "Should have 9 position levels"
        tiers = set(SENIORITY_MAP.values())
        assert tiers == {"Entry", "Mid", "Senior", "Management"}, "Should map to exactly 4 tiers"

    def test_no_unmapped_levels(self):
        """Ensure no None values in mapping"""
        assert all(v is not None for v in SENIORITY_MAP.values()), "All levels should map to a tier"

    def test_seniority_mapping_function(self, etl_instance):
        """Test the actual mapping function"""
        df = pd.DataFrame({
            'positionLevels': ['Executive', 'Manager', 'Fresh/entry level', 'Unknown']
        })

        df_mapped = etl_instance._map_seniority(df)

        assert df_mapped.loc[0, 'seniority_tier'] == 'Mid'
        assert df_mapped.loc[1, 'seniority_tier'] == 'Management'
        assert df_mapped.loc[2, 'seniority_tier'] == 'Entry'
        assert df_mapped.loc[3, 'seniority_tier'] == 'Unknown'  # Unmapped becomes Unknown


class TestSalaryCleaning:
    """Tests for three-stage salary cleaning"""

    def test_hard_bounds_applied(self, etl_instance):
        """Test salary floor and ceiling"""
        df = pd.DataFrame({
            'salary_minimum': [100.0, 500.0, 1000.0, 60000.0],
            'salary_maximum': [200.0, 1000.0, 5000.0, 70000.0],
        })

        df_clean = etl_instance._clean_salary(df)

        # Below floor should be null
        assert pd.isna(df_clean.loc[0, 'salary_minimum'])
        # Above ceiling should be null
        assert pd.isna(df_clean.loc[3, 'salary_minimum'])
        # Within bounds should remain
        assert df_clean.loc[1, 'salary_minimum'] == 500.0
        assert df_clean.loc[2, 'salary_minimum'] == 1000.0

    def test_min_max_swap(self, etl_instance):
        """Test inverted min/max are corrected"""
        df = pd.DataFrame({
            'salary_minimum': [5000.0],
            'salary_maximum': [3000.0],
        })

        df_clean = etl_instance._clean_salary(df)

        # Should be swapped
        assert df_clean.loc[0, 'salary_minimum'] == 3000.0
        assert df_clean.loc[0, 'salary_maximum'] == 5000.0

    def test_winsorization_applied(self, etl_instance):
        """Test that winsorization creates clean salary columns"""
        df = pd.DataFrame({
            'salary_minimum': [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
            'salary_maximum': [2000.0, 3000.0, 4000.0, 5000.0, 6000.0],
        })

        df_clean = etl_instance._clean_salary(df)

        # Should have clean salary columns
        assert 'salary_minimum_clean' in df_clean.columns
        assert 'salary_maximum_clean' in df_clean.columns
        assert 'average_salary_clean' in df_clean.columns

        # Clean salaries should not be null
        assert df_clean['average_salary_clean'].notna().all()


class TestCategoryParsing:
    """Tests for JSON category parsing"""

    def test_parse_categories_json(self, etl_instance):
        """Test parsing JSON categories"""
        df = pd.DataFrame({
            'categories': [
                '[{"id":21,"category":"Information Technology"}]',
                '[{"id":13,"category":"Banking and Financial Services"},{"id":25,"category":"Manufacturing"}]',
                '[]',
                None
            ]
        })

        df_parsed = etl_instance._parse_categories(df)

        assert df_parsed.loc[0, 'industry_list'] == ['Information Technology']
        assert df_parsed.loc[0, 'primary_industry'] == 'Information Technology'
        assert df_parsed.loc[0, 'industry_count'] == 1

        assert df_parsed.loc[1, 'industry_list'] == ['Banking and Financial Services', 'Manufacturing']
        assert df_parsed.loc[1, 'primary_industry'] == 'Banking and Financial Services'
        assert df_parsed.loc[1, 'industry_count'] == 2

        assert df_parsed.loc[2, 'industry_list'] == []
        assert df_parsed.loc[2, 'primary_industry'] == 'Unknown'

        assert df_parsed.loc[3, 'industry_list'] == []
        assert df_parsed.loc[3, 'primary_industry'] == 'Unknown'


class TestRoleExtraction:
    """Tests for role family keyword extraction"""

    def test_specific_roles_first(self, etl_instance):
        """Test that specific keywords match before generic ones"""
        df = pd.DataFrame({
            'title': [
                'Sales Manager',
                'Data Analyst',
                'Software Engineer',
                'Random Job Title',
                'nurse practitioner',
                None
            ]
        })

        df_classified = etl_instance._extract_role_family(df)

        # Sales should match before Manager (more specific)
        assert df_classified.loc[0, 'role_family'] == 'Sales'
        assert df_classified.loc[1, 'role_family'] == 'Analyst'
        assert df_classified.loc[2, 'role_family'] == 'Engineer'
        assert df_classified.loc[3, 'role_family'] == 'Other'
        assert df_classified.loc[4, 'role_family'] == 'Healthcare'
        assert df_classified.loc[5, 'role_family'] == 'Other'

    def test_role_keywords_coverage(self):
        """Verify ROLE_KEYWORDS dict is properly structured"""
        assert len(ROLE_KEYWORDS) > 0, "Should have role families defined"
        assert all(isinstance(v, list) for v in ROLE_KEYWORDS.values()), "All values should be lists"
        assert all(len(v) > 0 for v in ROLE_KEYWORDS.values()), "All families should have keywords"


class TestCompetitionRatio:
    """Tests for competition ratio calculation"""

    def test_divide_by_zero_handled(self, etl_instance):
        """Verify vacancies=0 results in NaN, not error"""
        df = pd.DataFrame({
            'metadata_totalNumberJobApplication': [10, 20, 30],
            'numberOfVacancies': [0, 5, 10],
            'title': ['Job1', 'Job2', 'Job3'],
            'positionLevels': ['Executive', 'Manager', 'Senior Executive'],
            'salary_minimum': [3000, 4000, 5000],
            'salary_maximum': [5000, 6000, 7000],
            'minimumYearsExperience': [2, 3, 5],
            'categories': ['[{"id":21,"category":"IT"}]'] * 3
        })

        # This should not raise ZeroDivisionError
        df_features = etl_instance._add_derived_features(df)

        assert pd.isna(df_features.loc[0, 'competition_ratio'])
        assert df_features.loc[1, 'competition_ratio'] == 4.0
        assert df_features.loc[2, 'competition_ratio'] == 3.0


class TestExperienceBands:
    """Tests for experience band assignment"""

    def test_experience_band_assignment(self, etl_instance):
        """Test that experience is properly banded"""
        df = pd.DataFrame({
            'minimumYearsExperience': [0, 1, 3, 5, 8, 15, None],
            'title': ['Job'] * 7,
            'positionLevels': ['Executive'] * 7,
            'salary_minimum': [3000] * 7,
            'salary_maximum': [5000] * 7,
            'numberOfVacancies': [1] * 7,
            'metadata_totalNumberJobApplication': [10] * 7,
            'categories': ['[{"id":21,"category":"IT"}]'] * 7
        })

        df_features = etl_instance._add_derived_features(df)

        assert df_features.loc[0, 'experience_band'] == '0-1 yr'
        assert df_features.loc[1, 'experience_band'] == '0-1 yr'
        assert df_features.loc[2, 'experience_band'] == '2-3 yrs'
        assert df_features.loc[3, 'experience_band'] == '4-5 yrs'
        assert df_features.loc[4, 'experience_band'] == '6-10 yrs'
        assert df_features.loc[5, 'experience_band'] == '10+ yrs'
        assert df_features.loc[6, 'experience_band'] == 'Unknown'


class TestDataQuality:
    """Tests for data quality checks"""

    def test_synthetic_rows_detection(self, etl_instance, sample_raw_data):
        """Test that synthetic rows are properly identified"""
        df_filtered = etl_instance._drop_synthetic_rows(sample_raw_data)

        # Should remove RANDOM_JOB_ row
        assert len(df_filtered) == 3
        assert 'RANDOM_JOB_999' not in df_filtered['metadata_jobPostId'].values

    def test_null_rows_removal(self, etl_instance):
        """Test that row-wide nulls are removed"""
        df = pd.DataFrame({
            'title': ['Job1', None, 'Job3'],
            'metadata_jobPostId': ['JOB1', 'JOB2', 'JOB3']
        })

        df_filtered = etl_instance._drop_null_rows(df)

        assert len(df_filtered) == 2
        assert df_filtered['title'].notna().all()


# Integration test
class TestPipelineIntegration:
    """Integration tests for full pipeline components"""

    def test_bronze_to_silver_workflow(self, etl_instance):
        """Test that Bronze output can be processed by Silver"""
        # This test would require Bronze data to exist
        # For now, just verify the methods exist
        assert hasattr(etl_instance, 'run_bronze')
        assert hasattr(etl_instance, 'run_silver')
        assert hasattr(etl_instance, 'run_gold')
        assert hasattr(etl_instance, 'run_all')

    def test_config_override(self):
        """Test that config can be overridden"""
        custom_config = {'SALARY_FLOOR': 1000}
        etl = SGJobsETL(config_override=custom_config)

        assert etl.config['SALARY_FLOOR'] == 1000

    def test_pipeline_summary_structure(self, etl_instance):
        """Test pipeline summary returns expected structure"""
        summary = etl_instance.pipeline_summary()

        assert 'bronze' in summary
        assert 'silver' in summary
        assert 'gold' in summary
        assert isinstance(summary['gold'], dict)
