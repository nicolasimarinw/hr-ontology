-- Cross-system DuckDB views for the HR data lake
-- These views join across source systems and become the basis for graph edges

-- =============================================================================
-- VIEW 1: Employee Full Profile (360-degree view)
-- Joins: HRIS + latest compensation + latest performance rating
-- =============================================================================
CREATE OR REPLACE VIEW employee_full_profile AS
WITH latest_salary AS (
    SELECT employee_id, amount AS current_salary, effective_date AS salary_date, reason AS salary_reason
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY effective_date DESC) AS rn
        FROM read_parquet('{lake}/compensation/base_salary.parquet')
    ) WHERE rn = 1
),
latest_review AS (
    SELECT employee_id, rating AS latest_rating, cycle_id AS review_cycle
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY cycle_id DESC) AS rn
        FROM read_parquet('{lake}/performance/performance_reviews.parquet')
    ) WHERE rn = 1
),
total_bonus AS (
    SELECT employee_id, SUM(amount) AS total_bonus_amount, COUNT(*) AS bonus_count
    FROM read_parquet('{lake}/compensation/bonuses.parquet')
    GROUP BY employee_id
),
total_equity AS (
    SELECT employee_id, SUM(shares) AS total_shares
    FROM read_parquet('{lake}/compensation/equity_grants.parquet')
    GROUP BY employee_id
)
SELECT
    e.*,
    d.name AS department_name,
    d.division_name,
    p.title AS position_title,
    ls.current_salary,
    ls.salary_date,
    lr.latest_rating,
    tb.total_bonus_amount,
    tb.bonus_count,
    te.total_shares,
    DATEDIFF('day', e.hire_date, COALESCE(e.termination_date, CURRENT_DATE)) / 365.25 AS tenure_years
FROM read_parquet('{lake}/hris/employees.parquet') e
LEFT JOIN read_parquet('{lake}/hris/departments.parquet') d ON e.department_id = d.dept_id
LEFT JOIN read_parquet('{lake}/hris/positions.parquet') p ON e.position_id = p.position_id
LEFT JOIN latest_salary ls ON e.employee_id = ls.employee_id
LEFT JOIN latest_review lr ON e.employee_id = lr.employee_id
LEFT JOIN total_bonus tb ON e.employee_id = tb.employee_id
LEFT JOIN total_equity te ON e.employee_id = te.employee_id;

-- =============================================================================
-- VIEW 2: Recruiting Funnel (source -> hire -> performance correlation)
-- Joins: ATS candidates/apps + HRIS employees + performance reviews
-- =============================================================================
CREATE OR REPLACE VIEW recruiting_funnel AS
WITH hired_apps AS (
    SELECT
        a.application_id,
        a.candidate_id,
        a.req_id,
        a.apply_date,
        c.name AS candidate_name,
        c.source,
        o.salary_offered,
        o.start_date
    FROM read_parquet('{lake}/ats/applications.parquet') a
    JOIN read_parquet('{lake}/ats/candidates.parquet') c ON a.candidate_id = c.candidate_id
    LEFT JOIN read_parquet('{lake}/ats/offers.parquet') o ON a.application_id = o.application_id
    WHERE a.status = 'Hired'
),
interview_scores AS (
    SELECT
        application_id,
        AVG(score) AS avg_interview_score,
        COUNT(*) AS interview_count
    FROM read_parquet('{lake}/ats/interviews.parquet')
    GROUP BY application_id
),
post_hire_performance AS (
    SELECT employee_id, AVG(rating) AS avg_rating, COUNT(*) AS review_count
    FROM read_parquet('{lake}/performance/performance_reviews.parquet')
    GROUP BY employee_id
)
SELECT
    ha.*,
    iscr.avg_interview_score,
    iscr.interview_count,
    e.employee_id,
    e.status AS current_status,
    e.termination_date,
    e.termination_reason,
    php.avg_rating AS post_hire_avg_rating,
    php.review_count AS post_hire_review_count,
    r.title AS req_title,
    r.department_id
FROM hired_apps ha
LEFT JOIN interview_scores iscr ON ha.application_id = iscr.application_id
LEFT JOIN read_parquet('{lake}/hris/employees.parquet') e ON ha.candidate_name = (e.first_name || ' ' || e.last_name)
LEFT JOIN post_hire_performance php ON e.employee_id = php.employee_id
LEFT JOIN read_parquet('{lake}/ats/requisitions.parquet') r ON ha.req_id = r.req_id;

-- =============================================================================
-- VIEW 3: Compensation Equity Analysis
-- Joins: Compensation + demographics + position for pay equity
-- =============================================================================
CREATE OR REPLACE VIEW compensation_equity AS
WITH latest_salary AS (
    SELECT employee_id, amount AS current_salary
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY effective_date DESC) AS rn
        FROM read_parquet('{lake}/compensation/base_salary.parquet')
    ) WHERE rn = 1
),
band_info AS (
    SELECT job_family, job_level, min_salary, midpoint, max_salary
    FROM read_parquet('{lake}/compensation/salary_bands.parquet')
)
SELECT
    e.employee_id,
    e.gender,
    e.ethnicity,
    e.job_level,
    e.job_family,
    e.department_id,
    e.status,
    d.name AS department_name,
    p.title AS position_title,
    ls.current_salary,
    b.midpoint AS band_midpoint,
    b.min_salary AS band_min,
    b.max_salary AS band_max,
    CASE WHEN b.midpoint > 0 THEN ROUND(ls.current_salary * 100.0 / b.midpoint, 1) ELSE NULL END AS compa_ratio,
    DATEDIFF('day', e.hire_date, COALESCE(e.termination_date, CURRENT_DATE)) / 365.25 AS tenure_years
FROM read_parquet('{lake}/hris/employees.parquet') e
LEFT JOIN latest_salary ls ON e.employee_id = ls.employee_id
LEFT JOIN read_parquet('{lake}/hris/departments.parquet') d ON e.department_id = d.dept_id
LEFT JOIN read_parquet('{lake}/hris/positions.parquet') p ON e.position_id = p.position_id
LEFT JOIN band_info b ON e.job_family = b.job_family AND e.job_level = b.job_level;

-- =============================================================================
-- VIEW 4: Flight Risk Features
-- Joins: Performance + compensation + tenure + manager quality
-- =============================================================================
CREATE OR REPLACE VIEW flight_risk_features AS
WITH latest_salary AS (
    SELECT employee_id, amount AS current_salary
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY effective_date DESC) AS rn
        FROM read_parquet('{lake}/compensation/base_salary.parquet')
    ) WHERE rn = 1
),
salary_history AS (
    SELECT employee_id, COUNT(*) AS salary_changes,
           MAX(amount) - MIN(amount) AS salary_growth
    FROM read_parquet('{lake}/compensation/base_salary.parquet')
    GROUP BY employee_id
),
performance_trend AS (
    SELECT employee_id,
           AVG(rating) AS avg_rating,
           COUNT(*) AS review_count,
           MAX(rating) - MIN(rating) AS rating_variance
    FROM read_parquet('{lake}/performance/performance_reviews.parquet')
    GROUP BY employee_id
),
manager_quality AS (
    SELECT
        reviewer_id AS manager_id,
        AVG(rating) AS avg_team_rating,
        COUNT(DISTINCT employee_id) AS team_size
    FROM read_parquet('{lake}/performance/performance_reviews.parquet')
    GROUP BY reviewer_id
),
band_info AS (
    SELECT job_family, job_level, midpoint
    FROM read_parquet('{lake}/compensation/salary_bands.parquet')
)
SELECT
    e.employee_id,
    e.first_name || ' ' || e.last_name AS full_name,
    e.department_id,
    e.job_level,
    e.job_family,
    e.gender,
    e.ethnicity,
    e.status,
    DATEDIFF('day', e.hire_date, COALESCE(e.termination_date, CURRENT_DATE)) / 365.25 AS tenure_years,
    ls.current_salary,
    CASE WHEN b.midpoint > 0 THEN ROUND(ls.current_salary * 100.0 / b.midpoint, 1) ELSE NULL END AS compa_ratio,
    sh.salary_changes,
    sh.salary_growth,
    pt.avg_rating,
    pt.review_count,
    pt.rating_variance,
    mq.avg_team_rating AS manager_avg_team_rating,
    mq.team_size AS manager_team_size,
    -- Simple flight risk score (higher = more risk)
    CASE
        WHEN e.status = 'Terminated' THEN NULL
        ELSE ROUND(
            (CASE WHEN DATEDIFF('day', e.hire_date, CURRENT_DATE) / 365.25 BETWEEN 1.5 AND 3 THEN 20 ELSE 0 END) +
            (CASE WHEN ls.current_salary < b.midpoint * 0.9 THEN 25 ELSE 0 END) +
            (CASE WHEN pt.avg_rating < 3.5 THEN 15 ELSE 0 END) +
            (CASE WHEN sh.salary_changes <= 1 THEN 15 ELSE 0 END) +
            (CASE WHEN mq.avg_team_rating < 3.5 THEN 15 ELSE 0 END) +
            (CASE WHEN mq.team_size > 10 THEN 10 ELSE 0 END)
        , 1) END AS flight_risk_score
FROM read_parquet('{lake}/hris/employees.parquet') e
LEFT JOIN latest_salary ls ON e.employee_id = ls.employee_id
LEFT JOIN salary_history sh ON e.employee_id = sh.employee_id
LEFT JOIN performance_trend pt ON e.employee_id = pt.employee_id
LEFT JOIN manager_quality mq ON e.manager_id = mq.manager_id
LEFT JOIN band_info b ON e.job_family = b.job_family AND e.job_level = b.job_level
WHERE e.status = 'Active';
