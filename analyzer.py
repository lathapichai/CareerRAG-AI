
import re


# Canonical skill names used throughout the application.
# Alternative names are normalized to one skill.
SKILL_ALIASES = {
    "python": ["python"],
    "java": ["java"],
    "sql": ["sql", "sql queries", "structured query language"],
    "mysql": ["mysql", "my sql"],
    "postgresql": ["postgresql", "postgres", "postgres db"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "javascript": ["javascript", "java script", "js"],
    "flask": ["flask"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "py torch"],
    "opencv": ["opencv", "open cv"],
    "yolo": ["yolo", "you only look once"],
    "pandas": ["pandas"],
    "numpy": ["numpy", "num py"],
    "git": ["git"],
    "github": ["github", "git hub"],
    "rest apis": [
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "rest api integration",
        "restful api integration",
    ],
    "object-oriented programming": [
        "oop",
        "object-oriented programming",
        "object oriented programming",
        "object-oriented programing",
        "object oriented programing",
    ],
    "data structures and algorithms": [
        "data structures and algorithms",
        "data structure and algorithms",
        "data structures & algorithms",
        "dsa",
    ],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
}


def _normalize_text(text):
    """Convert text into a consistent format for matching."""
    text = str(text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains_phrase(text, phrase):
    """Check whether a complete skill phrase occurs in the text."""
    normalized_text = _normalize_text(text)
    normalized_phrase = _normalize_text(phrase)

    # Flexible whitespace supports phrases split across spaces or lines.
    pattern = (
        r"(?<!\w)"
        + r"\s+".join(re.escape(part) for part in normalized_phrase.split())
        + r"(?!\w)"
    )

    return re.search(pattern, normalized_text) is not None


def _canonical_skill(skill):
    """Convert a recognized skill or alias into its canonical name."""
    normalized_skill = _normalize_text(skill)

    for canonical_name, aliases in SKILL_ALIASES.items():
        if normalized_skill == _normalize_text(canonical_name):
            return canonical_name

        if any(
            normalized_skill == _normalize_text(alias)
            for alias in aliases
        ):
            return canonical_name

    # Preserve unknown skills instead of silently deleting them.
    return normalized_skill


def _normalize_skill_list(skills):
    """Normalize skills and remove duplicates while preserving order."""
    normalized = []

    for skill in skills or []:
        canonical = _canonical_skill(skill)

        if canonical and canonical not in normalized:
            normalized.append(canonical)

    return normalized


def extract_skills(text):
    """Extract technical skills and normalize alternative names."""

    text = _normalize_text(text)
    found_skills = []

    for canonical_name, aliases in SKILL_ALIASES.items():
        all_names = [canonical_name] + aliases

        if any(_contains_phrase(text, alias) for alias in all_names):
            found_skills.append(canonical_name)

    # Canonical skill names are unique, so OOP and
    # Object-Oriented Programming cannot be counted separately.
    return found_skills


def compare_skills(resume_skills, job_skills):
    """Compare normalized resume skills against job requirements."""

    resume_set = set(_normalize_skill_list(resume_skills))
    job_set = set(_normalize_skill_list(job_skills))

    matching = sorted(resume_set.intersection(job_set))
    missing = sorted(job_set - resume_set)

    return matching, missing


def calculate_match_percentage(resume_skills, job_skills):
    """Calculate the percentage of unique required skills matched."""

    resume_set = set(_normalize_skill_list(resume_skills))
    job_set = set(_normalize_skill_list(job_skills))

    if not job_set:
        return 0.0

    matching = resume_set.intersection(job_set)
    percentage = (len(matching) / len(job_set)) * 100

    return round(percentage, 2)
