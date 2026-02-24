"""Few-shot examples mapping natural language questions to Cypher/SQL queries."""

EXAMPLE_QUERIES = [
    {
        "question": "Who are the top flight risks in Engineering and what would happen if they left?",
        "approach": "graph",
        "query": """
MATCH (e:Employee)-[:BELONGS_TO]->(d:Department)-[:PART_OF]->(div:Division {name: 'Engineering'})
WHERE e.status = 'Active'
OPTIONAL MATCH (report:Employee)-[:REPORTS_TO]->(e)
WITH e, d, COUNT(report) AS direct_reports
OPTIONAL MATCH (e)-[:HAS_SKILL]->(s:Skill)
WITH e, d, direct_reports, COUNT(s) AS skill_count
WITH e, d, direct_reports, skill_count,
     (direct_reports * 10 + skill_count * 2) AS impact_score
ORDER BY impact_score DESC
LIMIT 10
RETURN e.employee_id AS id, e.first_name + ' ' + e.last_name AS name,
       e.job_level AS level, d.name AS department,
       direct_reports, skill_count, impact_score
""",
    },
    {
        "question": "Is there a pay equity gap by gender for senior engineers?",
        "approach": "sql",
        "query": """
SELECT e.gender,
       e.job_level,
       COUNT(*) AS headcount,
       ROUND(AVG(bs.amount), 0) AS avg_salary,
       ROUND(MEDIAN(bs.amount), 0) AS median_salary,
       ROUND(MIN(bs.amount), 0) AS min_salary,
       ROUND(MAX(bs.amount), 0) AS max_salary
FROM employees e
JOIN base_salary bs ON e.employee_id = bs.employee_id
WHERE e.status = 'Active'
  AND e.job_family = 'Software Engineering'
  AND e.job_level IN ('L3', 'L4', 'M1', 'M2')
  AND bs.effective_date = (
      SELECT MAX(bs2.effective_date)
      FROM base_salary bs2
      WHERE bs2.employee_id = e.employee_id
  )
GROUP BY e.gender, e.job_level
ORDER BY e.job_level, e.gender
""",
    },
    {
        "question": "Which recruiting sources produce the highest-performing hires?",
        "approach": "sql",
        "query": """
SELECT c.source,
       COUNT(DISTINCT e.employee_id) AS hires,
       ROUND(AVG(pr.rating), 2) AS avg_rating,
       ROUND(AVG(CASE WHEN e.status = 'Terminated' THEN 1.0 ELSE 0.0 END) * 100, 1) AS turnover_pct
FROM candidates c
JOIN applications a ON c.candidate_id = a.candidate_id
JOIN offers o ON a.application_id = o.application_id
JOIN employees e ON e.email = c.email
LEFT JOIN performance_reviews pr ON pr.employee_id = e.employee_id
WHERE o.status = 'Accepted'
GROUP BY c.source
HAVING COUNT(DISTINCT e.employee_id) >= 3
ORDER BY avg_rating DESC
""",
    },
    {
        "question": "Which managers have the widest span of control?",
        "approach": "graph",
        "query": """
MATCH (manager:Employee)<-[:REPORTS_TO]-(report:Employee)
WHERE manager.status = 'Active'
WITH manager, COUNT(report) AS direct_reports
ORDER BY direct_reports DESC
LIMIT 15
MATCH (manager)-[:BELONGS_TO]->(d:Department)
RETURN manager.employee_id AS id,
       manager.first_name + ' ' + manager.last_name AS name,
       manager.job_level AS level,
       d.name AS department,
       direct_reports
""",
    },
    {
        "question": "What skills are most common among top performers?",
        "approach": "graph",
        "query": """
MATCH (e:Employee)-[:REVIEWED_IN]->(r:PerformanceReview)
WHERE r.rating >= 4.0 AND e.status = 'Active'
WITH DISTINCT e
MATCH (e)-[:HAS_SKILL]->(s:Skill)
WITH s.name AS skill, s.category AS category, COUNT(DISTINCT e) AS top_performer_count
ORDER BY top_performer_count DESC
LIMIT 15
RETURN skill, category, top_performer_count
""",
    },
    {
        "question": "If our VP of Engineering leaves, map the full organizational impact",
        "approach": "algorithm",
        "algorithm": "cascade",
        "note": "First find the VP, then run cascade_impact with their employee_id",
    },
    {
        "question": "Show me the promotion velocity by gender over the last 2 years",
        "approach": "sql",
        "query": """
SELECT e.gender,
       COUNT(*) AS promotions,
       ROUND(AVG(DATEDIFF('month', e.hire_date, eh.effective_date)), 1) AS avg_months_to_promote
FROM employment_history eh
JOIN employees e ON eh.employee_id = e.employee_id
WHERE eh.event_type = 'promotion'
  AND eh.effective_date >= '2024-01-01'
GROUP BY e.gender
ORDER BY e.gender
""",
    },
    {
        "question": "Which departments have the most cross-department skill overlap?",
        "approach": "graph",
        "query": """
MATCH (e1:Employee)-[:HAS_SKILL]->(s:Skill)<-[:HAS_SKILL]-(e2:Employee)
WHERE e1.department_id < e2.department_id
  AND e1.status = 'Active' AND e2.status = 'Active'
WITH e1.department_id AS dept1, e2.department_id AS dept2,
     COUNT(DISTINCT s) AS shared_skills
ORDER BY shared_skills DESC
LIMIT 10
RETURN dept1, dept2, shared_skills
""",
    },
]
