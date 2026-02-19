"""
Pytest fixtures for SGJobsETL testing
"""

import pytest
import pandas as pd
import numpy as np
from src.etl.sg_jobs_etl import SGJobsETL


@pytest.fixture
def sample_raw_data():
    """Minimal sample DataFrame for testing"""
    return pd.DataFrame({
        'metadata_jobPostId': ['JOB001', 'RANDOM_JOB_999', 'JOB002', 'JOB003'],
        'title': ['Data Analyst', 'Test Job', 'Software Engineer', 'Sales Manager'],
        'salary_minimum': [3000.0, 250000.0, 4000.0, 2500.0],
        'salary_maximum': [5000.0, 300000.0, 6000.0, 4500.0],
        'positionLevels': ['Executive', 'Manager', 'Junior Executive', 'Senior Executive'],
        'numberOfVacancies': [2, 1, 5, 3],
        'metadata_totalNumberJobApplication': [50, 10, 100, 30],
        'categories': [
            '[{"id":21,"category":"Information Technology"}]',
            '[{"id":13,"category":"Banking and Financial Services"}]',
            '[{"id":21,"category":"Information Technology"}]',
            '[{"id":25,"category":"Sales"}]'
        ],
        'employmentTypes': ['Full Time', 'Contract', 'Full Time', 'Permanent']
    })


@pytest.fixture
def etl_instance():
    """ETL instance for testing"""
    return SGJobsETL()


@pytest.fixture
def sample_silver_data():
    """Sample Silver-like data with enriched features"""
    return pd.DataFrame({
        'title': ['Data Analyst', 'Software Engineer', 'Sales Manager'],
        'role_family': ['Analyst', 'Developer', 'Sales'],
        'seniority_tier': ['Mid', 'Mid', 'Senior'],
        'average_salary_clean': [4000.0, 5000.0, 3500.0],
        'salary_minimum_clean': [3000.0, 4000.0, 2500.0],
        'salary_maximum_clean': [5000.0, 6000.0, 4500.0],
        'numberOfVacancies': [2, 5, 3],
        'metadata_totalNumberJobApplication': [50, 100, 30],
        'competition_ratio': [25.0, 20.0, 10.0],
        'experience_band': ['2-3 yrs', '4-5 yrs', '6-10 yrs'],
        'primary_industry': ['Information Technology', 'Information Technology', 'Sales'],
        'industry_list': [
            ['Information Technology'],
            ['Information Technology', 'Software'],
            ['Sales', 'Business Development']
        ]
    })
