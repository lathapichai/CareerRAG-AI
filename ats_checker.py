
import re


def check_ats(resume_text, job_description=""):
    """
    Perform basic ATS-friendly resume checks.

    This is a rule-based screening helper, not a real ATS simulator.
    """

    if not resume_text or not resume_text.strip():
        return {
            "score": 0,
            "status": "Cannot check",
            "checks": [],
            "missing_keywords": [],
            "recommendations": ["Upload a resume containing readable text."]
        }

    text = resume_text.strip()
    lower_text = text.lower()

    checks = []
    recommendations = []

    def add_check(name, passed, details):
        checks.append({
            "check": name,
            "passed": passed,
            "details": details
        })

    # 1. Resume length
    word_count = len(text.split())
    length_ok = 150 <= word_count <= 1200

    add_check(
        "Resume length",
        length_ok,
        f"Detected approximately {word_count} words."
    )

    if word_count < 150:
        recommendations.append(
            "Add relevant education, projects, skills, and experience "
            "if the resume is too short."
        )
    elif word_count > 1200:
        recommendations.append(
            "Consider removing irrelevant or repetitive content."
        )

    # 2. Contact information
    email_found = bool(
        re.search(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            text,
            re.IGNORECASE
        )
    )

    phone_found = bool(
        re.search(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)", text)
    )

    add_check(
        "Email address",
        email_found,
        "Email address detected." if email_found
        else "No email address detected."
    )

    if not email_found:
        recommendations.append(
            "Add a professional email address to your resume."
        )

    add_check(
        "Phone number",
        phone_found,
        "A possible phone number was detected." if phone_found
        else "No likely phone number was detected."
    )

    if not phone_found:
        recommendations.append(
            "Add your phone number if appropriate for the application."
        )

    # 3. Common resume sections
    section_patterns = {
        "Education": r"\b(education|academic background|qualification)\b",
        "Skills": r"\b(technical skills|skills|core competencies)\b",
        "Projects": r"\b(projects|academic projects|personal projects)\b",
        "Experience": r"\b(experience|internship|work history)\b"
    }

    for section, pattern in section_patterns.items():
        found = bool(re.search(pattern, lower_text))

        add_check(
            f"{section} section",
            found,
            f"{section} section detected." if found
            else f"No recognizable {section.lower()} heading detected."
        )

        if not found:
            recommendations.append(
                f"Consider adding a clearly labelled {section} section "
                "if relevant to your background."
            )

    # 4. Readability and common formatting checks
    replacement_chars = text.count("\ufffd")
    text_readable = replacement_chars == 0

    add_check(
        "Extracted text readability",
        text_readable,
        "No replacement characters detected." if text_readable
        else "Some extracted characters may be corrupted."
    )

    if not text_readable:
        recommendations.append(
            "Review the original document for corrupted characters "
            "or extraction issues."
        )

    # 5. Job-description keyword comparison
    missing_keywords = []

    if job_description and job_description.strip():
        # Keep this list focused on common technical terms.
        keyword_candidates = [
            "python", "java", "sql", "mysql", "postgresql",
            "html", "css", "javascript", "flask",
            "machine learning", "deep learning",
            "tensorflow", "pytorch", "opencv",
            "git", "github", "rest api", "rest apis",
            "object-oriented programming", "oop",
            "data structures", "docker", "kubernetes",
            "aws", "azure", "communication", "problem solving"
        ]

        jd_lower = job_description.lower()

        required_keywords = []

        for keyword in keyword_candidates:
            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, jd_lower):
                required_keywords.append(keyword)

        # Recognize common equivalent expressions.
        resume_keywords = set()

        for keyword in required_keywords:
            if re.search(
                r"\b" + re.escape(keyword) + r"\b",
                lower_text
            ):
                resume_keywords.add(keyword)

        # Do not count the same REST API concept twice.
        if "rest api" in resume_keywords or "rest apis" in resume_keywords:
            resume_keywords.update({"rest api", "rest apis"})

        missing_keywords = [
            keyword for keyword in required_keywords
            if keyword not in resume_keywords
        ]

        add_check(
            "Job-description keywords",
            len(missing_keywords) == 0,
            (
                "All detected keywords were found."
                if not missing_keywords
                else "Some job-description keywords were not detected."
            )
        )

        if missing_keywords:
            recommendations.append(
                "Review these job-description keywords and include "
                "only those that truthfully reflect your skills: "
                + ", ".join(missing_keywords)
                + "."
            )

    # 6. Calculate a transparent rule-based score.
    passed_checks = sum(
        1 for item in checks if item["passed"]
    )

    score = round(
        (passed_checks / len(checks)) * 100, 2
    ) if checks else 0

    if score >= 80:
        status = "Good on the checks performed"
    elif score >= 60:
        status = "Some improvements recommended"
    else:
        status = "Several improvements recommended"

    if not recommendations:
        recommendations.append(
            "No issues were detected by these basic checks. "
            "Review the resume manually before applying."
        )

    return {
        "score": score,
        "status": status,
        "word_count": word_count,
        "checks": checks,
        "missing_keywords": missing_keywords,
        "recommendations": recommendations
    }
