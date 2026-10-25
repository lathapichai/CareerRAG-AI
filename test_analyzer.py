
from analyzer import (
    extract_skills,
    compare_skills,
    calculate_match_percentage,
)

# Test 1: OOP aliases
resume = "Python, OOP, Java"
job = "Python, Object-Oriented Programming, Java"

resume_skills = extract_skills(resume)
job_skills = extract_skills(job)

print("Test 1: OOP aliases")
print("Resume skills:", resume_skills)
print("Job skills:", job_skills)
print("Comparison:", compare_skills(resume_skills, job_skills))
print("Match:", calculate_match_percentage(resume_skills, job_skills))

# Test 2: SQL, MySQL and PostgreSQL
resume = "MySQL and PostgreSQL"
job = "SQL, MySQL and PostgreSQL"

resume_skills = extract_skills(resume)
job_skills = extract_skills(job)

print("\nTest 2: Database skills")
print("Resume skills:", resume_skills)
print("Job skills:", job_skills)
print("Comparison:", compare_skills(resume_skills, job_skills))
print("Match:", calculate_match_percentage(resume_skills, job_skills))

# Test 3: Duplicate skills
resume = "Python, Python, PyTorch"
job = "Python, PyTorch, Docker"

resume_skills = extract_skills(resume)
job_skills = extract_skills(job)

print("\nTest 3: Duplicate skills")
print("Comparison:", compare_skills(resume_skills, job_skills))
print("Match:", calculate_match_percentage(resume_skills, job_skills))
