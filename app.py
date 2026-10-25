
import hashlib
from pathlib import Path

import streamlit as st

from resume_parser import extract_text_from_docx, extract_text_from_pdf
from analyzer import extract_skills, compare_skills
from ats_checker import check_ats
from web_search import search_web
from llm import ask_gemini
from rag import search_knowledge


# ==========================================
# 1. APP CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="CareerRAG AI",
    page_icon="🎯",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. SESSION STATE
# ==========================================

defaults = {
    "resume_text": "",
    "jd_text": "",
    "resume_name": "",
    "jd_name": "",
    "analysis": None,
    "messages": [],
    "resume_hash": "",
    "jd_hash": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# 3. DOCUMENT HELPERS
# ==========================================

def save_uploaded_file(uploaded_file):
    """Save an uploaded file and return its path and hash."""

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    safe_name = Path(uploaded_file.name).name
    destination = UPLOAD_DIR / f"{file_hash[:12]}_{safe_name}"
    destination.write_bytes(file_bytes)

    return destination, file_hash


def extract_document_text(uploaded_file):
    """Extract text from a PDF or DOCX document."""

    if uploaded_file is None:
        return "", ""

    file_path, file_hash = save_uploaded_file(uploaded_file)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        text = extract_text_from_pdf(str(file_path))
    elif extension == ".docx":
        text = extract_text_from_docx(str(file_path))
    else:
        raise ValueError("Please upload a PDF or DOCX file.")

    return text, file_hash


# ==========================================
# 4. SKILL ANALYSIS HELPERS
# ==========================================

def normalize_skills(skills):
    """Normalize analyzer output into a list."""

    if skills is None:
        return []

    if isinstance(skills, str):
        return [skills.strip()] if skills.strip() else []

    if isinstance(skills, dict):
        return list(skills.keys())

    try:
        return list(skills)
    except TypeError:
        return [str(skills)]


def get_skill_comparison(resume_skills, jd_skills):
    """Compare skills and normalize the result."""

    comparison = compare_skills(resume_skills, jd_skills)

    if isinstance(comparison, dict):
        matching = comparison.get(
            "matching_skills",
            comparison.get("matching", []),
        )
        missing = comparison.get(
            "missing_skills",
            comparison.get("missing", []),
        )

    elif isinstance(comparison, (tuple, list)) and len(comparison) >= 2:
        matching, missing = comparison[0], comparison[1]

    else:
        resume_set = {
            str(skill).strip().lower()
            for skill in resume_skills
        }
        jd_set = {
            str(skill).strip().lower()
            for skill in jd_skills
        }

        matching = [
            skill for skill in resume_skills
            if str(skill).strip().lower() in jd_set
        ]
        missing = [
            skill for skill in jd_skills
            if str(skill).strip().lower() not in resume_set
        ]

    return normalize_skills(matching), normalize_skills(missing)


# ==========================================
# 5. RESULT FORMATTING
# ==========================================

def format_result(result, indent=0):
    """Format dictionaries and lists as readable Markdown."""

    prefix = "  " * indent

    if isinstance(result, dict):
        lines = []

        for key, value in result.items():
            label = str(key).replace("_", " ").replace("-", " ").title()

            if isinstance(value, (dict, list, tuple, set)):
                lines.append(f"{prefix}**{label}:**")
                nested = format_result(value, indent + 1)

                if nested:
                    lines.append(nested)
            else:
                lines.append(f"{prefix}- **{label}:** {value}")

        return "\n".join(lines)

    if isinstance(result, (list, tuple, set)):
        lines = []

        for item in result:
            if isinstance(item, (dict, list, tuple, set)):
                lines.append(f"{prefix}-")
                lines.append(format_result(item, indent + 1))
            else:
                lines.append(f"{prefix}- {item}")

        return "\n".join(lines)

    return f"{prefix}{result}"


def format_ats_result(ats_result):
    """Format ATS results for readable chat output."""

    if not isinstance(ats_result, dict):
        return format_result(ats_result)

    lines = ["## ATS Checklist Results"]

    score = ats_result.get("score")
    status = ats_result.get("status")
    word_count = ats_result.get("word_count")

    if score is not None:
        lines.append(f"- **Score:** {score}")

    if status:
        lines.append(f"- **Status:** {status}")

    if word_count is not None:
        lines.append(f"- **Resume word count:** {word_count}")

    checks = ats_result.get("checks", [])

    if checks:
        lines.append("\n### Individual Checks")

        for check in checks:
            if not isinstance(check, dict):
                lines.append(f"- {check}")
                continue

            name = check.get("check", "Unnamed check")
            passed = check.get("passed", False)
            details = check.get("details", "")

            symbol = "✅" if passed else "⚠️"
            result_text = "Passed" if passed else "Needs attention"

            lines.append(f"- {symbol} **{name}:** {result_text}")

            if details:
                lines.append(f"  - {details}")

    missing_keywords = ats_result.get("missing_keywords", [])

    if missing_keywords:
        lines.append("\n### Missing ATS Keywords")
        lines.extend(f"- {keyword}" for keyword in missing_keywords)

    recommendations = ats_result.get("recommendations", [])

    if recommendations:
        lines.append("\n### Recommendations")

        if isinstance(recommendations, list):
            lines.extend(f"- {item}" for item in recommendations)
        else:
            lines.append(f"- {recommendations}")

    return "\n".join(lines)


# ==========================================
# 6. WEB SEARCH HELPERS
# ==========================================

def needs_web_search(question):
    """Identify questions that may benefit from web search."""

    keywords = [
        "latest",
        "current",
        "today",
        "recent",
        "job opening",
        "job openings",
        "vacancy",
        "vacancies",
        "recruitment",
        "apply",
        "application deadline",
        "salary",
        "stipend",
        "certification",
        "certificate",
        "official link",
        "internship",
        "news",
        "2027 jobs",
        "hiring",
        "job opportunities",
        "free course",
        "course link",
        "learning resources",
        "resource links",
        "free learning resources",
        "official documentation",
        "tutorial links",
        "learning roadmap",
        "roadmap resources",
        "free tutorials",
        "documentation link",
    ]

    question_lower = question.lower()
    return any(keyword in question_lower for keyword in keywords)


def retrieve_web_context(question):
    """Search the web and format returned results."""

    try:
        result = search_web(question)

        if not result:
            return "No web results were returned."

        return format_result(result)

    except Exception as error:
        print(f"Web search error: {type(error).__name__}: {error}")

        return (
            "Web search is currently unavailable. "
            "Current information could not be verified."
        )


# ==========================================
# 7. DASHBOARD CONTEXT
# ==========================================

def build_analysis_context():
    """Provide Gemini with the stored dashboard results."""

    result = st.session_state.analysis

    if not result:
        return "Resume analysis has not been run yet."

    ats_result = result.get("ats_result", "Not available")
    matching = result.get("matching_skills", [])
    missing = result.get("missing_skills", [])
    percentage = result.get("match_percentage")

    percentage_text = (
        f"{percentage}%"
        if percentage is not None
        else "N/A - no job description skills detected"
    )

    return f"""
DASHBOARD ANALYSIS - AUTHORITATIVE RESULTS

RESUME SKILLS DETECTED:
{result.get("resume_skills", [])}

JOB DESCRIPTION SKILLS DETECTED:
{result.get("jd_skills", [])}

EXACT MATCHING SKILLS:
{matching}

EXACT MISSING SKILLS:
{missing}

EXACT SKILL MATCH PERCENTAGE:
{percentage_text}

NUMBER OF MATCHING SKILLS: {len(matching)}
NUMBER OF MISSING SKILLS: {len(missing)}

ATS CHECKLIST RESULTS:
{format_ats_result(ats_result)}

IMPORTANT:
These results were calculated by the project's Python analyzer.
Use the exact lists and percentage when discussing the dashboard.
Do not independently recalculate or reclassify them.
"""


# ==========================================
# 8. DIRECT DASHBOARD ANSWERS
# ==========================================

def answer_from_dashboard(question):
    """Answer factual dashboard questions directly from Python."""

    result = st.session_state.get("analysis")
    if not result:
        return None

    q = " ".join(question.lower().strip().split())

    matching = result.get("matching_skills", []) or []
    missing = result.get("missing_skills", []) or []
    resume_skills = result.get("resume_skills", []) or []
    jd_skills = result.get("jd_skills", []) or []
    percentage = result.get("match_percentage")
    ats_result = result.get("ats_result", "Not available")

    # Handle combined dashboard + learning-priority questions directly.
    # This prevents Gemini from answering with unrelated project advice.
    asks_both_skill_lists = (
        "matching skills" in q and "missing skills" in q
    ) or "matching and missing skills" in q
    asks_for_priorities = any(term in q for term in (
        "suggest", "recommend", "top three", "top 3", "learn first",
        "improve my chances", "shortlisted", "should i learn",
        "skills to learn", "prioritize", "prioritise",
    ))

    if asks_both_skill_lists and asks_for_priorities:
        percentage_text = (
            f"{percentage}%" if percentage is not None
            else "N/A — add a job description with detectable skills first."
        )
        matching_text = "\n".join(f"- {skill}" for skill in matching)
        missing_text = "\n".join(f"- {skill}" for skill in missing)

        # Recommendations must be selected only from the dashboard's missing list.
        priority_order = ("sql", "git", "rest apis", "github",
                          "object-oriented programming", "docker",
                          "aws", "azure", "kubernetes")
        missing_by_lower = {str(skill).strip().lower(): skill for skill in missing}
        recommended = []
        for preferred in priority_order:
            if preferred in missing_by_lower:
                recommended.append(missing_by_lower[preferred])
            if len(recommended) == 3:
                break
        # If the dashboard uses different labels, fill from its own list only.
        for skill in missing:
            if len(recommended) == 3:
                break
            if skill not in recommended:
                recommended.append(skill)

        reasons = {
            "sql": "Builds the foundation for querying and working with databases.",
            "git": "Helps track code changes and collaborate safely on projects.",
            "rest apis": "Helps Python applications communicate with other services.",
            "github": "Helps you publish projects and show your code to recruiters.",
            "object-oriented programming": "Strengthens core programming and code-organization skills.",
            "docker": "Introduces packaging applications into portable containers.",
            "aws": "Introduces cloud deployment and commonly used cloud services.",
            "azure": "Introduces cloud deployment and Microsoft cloud services.",
            "kubernetes": "Is useful after learning container basics such as Docker.",
        }
        recommendation_lines = []
        for index, skill in enumerate(recommended, start=1):
            reason = reasons.get(
                str(skill).strip().lower(),
                "This is listed as missing in your dashboard, so it is a candidate for focused practice.",
            )
            recommendation_lines.append(f"{index}. **{skill}** — {reason}")

        return (
            "## Complete Dashboard Skill Analysis\n\n"
            f"**Skill match percentage:** {percentage_text}\n\n"
            f"**Matching skills ({len(matching)}):**\n\n"
            f"{matching_text or '- None detected'}\n\n"
            f"**Missing skills ({len(missing)}):**\n\n"
            f"{missing_text or '- None detected'}\n\n"
            "## Suggested learning priorities\n\n"
            + ("\n".join(recommendation_lines) if recommendation_lines else
               "No missing skills are listed in the dashboard, so there are no missing skills to prioritize.")
            + "\n\nThese are suggested starting priorities, not a guarantee of shortlisting. The matching and missing lists above are copied from your dashboard without recalculation."
        )

    # Keep general advice, learning plans, and recommendations with Gemini.
    advice_phrases = (
        "how can i", "how do i", "how should i", "how to learn",
        "learning plan", "study plan", "roadmap", "teach me",
        "recommend a course", "course recommendation", "explain how",
        "prepare for interview", "interview preparation", "give me a plan",
        "steps to improve", "how to improve", "help me improve",
        "learning resources", "resource links", "tutorial links",
        "free courses", "free resources",
    )
    if any(phrase in q for phrase in advice_phrases):
        return None

    matching = result.get("matching_skills", []) or []
    missing = result.get("missing_skills", []) or []
    resume_skills = result.get("resume_skills", []) or []
    jd_skills = result.get("jd_skills", []) or []
    percentage = result.get("match_percentage")
    ats_result = result.get("ats_result", "Not available")

    percentage_text = (
        f"{percentage}%" if percentage is not None
        else "N/A — add a job description with detectable skills first."
    )

    # Detect whether the user asks for a complete set of dashboard results.
    asks_complete_analysis = any(phrase in q for phrase in (
        "complete skill analysis", "full skill analysis",
        "complete skills analysis", "complete skill comparison",
        "full skill comparison", "complete dashboard analysis",
        "complete analysis", "all skill results",
        "matching skills and missing skills",
    ))

    asks_percentage = any(phrase in q for phrase in (
        "match percentage", "matching percentage", "match percent",
        "match score", "match rate", "resume match", "percentage match",
        "what percentage", "how much does my resume match",
        "how well does my resume match", "skill match",
    ))

    asks_matching = any(phrase in q for phrase in (
        "matching skills", "matched skills", "skills that match",
        "which skills match", "what skills match", "skills matched",
    ))

    asks_missing = any(phrase in q for phrase in (
        "what skills are missing", "which skills are missing",
        "missing skills", "skills missing", "skill gaps",
        "what am i missing", "skills i lack", "what skills should i learn",
    ))

    # IMPORTANT: complete-analysis handling must happen before individual
    # percentage handling, otherwise the function returns only the score.
    if asks_complete_analysis or (asks_percentage and asks_matching and asks_missing):
        matching_text = "\n".join(f"- {skill}" for skill in matching)
        missing_text = "\n".join(f"- {skill}" for skill in missing)
        return (
            "## Complete Dashboard Skill Analysis\n\n"
            f"**Skill match percentage:** {percentage_text}\n\n"
            f"**Matching skills ({len(matching)}):**\n\n"
            f"{matching_text or '- None detected'}\n\n"
            f"**Missing skills ({len(missing)}):**\n\n"
            f"{missing_text or '- None detected'}"
        )

    if asks_percentage:
        return f"**Dashboard skill match:** {percentage_text}"

    if asks_matching:
        items = "\n".join(f"- {skill}" for skill in matching)
        return f"**Matching skills ({len(matching)}):**\n\n{items or '- None detected'}"

    if asks_missing:
        items = "\n".join(f"- {skill}" for skill in missing)
        return f"**Missing skills ({len(missing)}):**\n\n{items or '- None detected'}"

    resume_skill_phrases = (
        "resume skills", "skills in my resume", "skills detected in my resume",
        "detected resume skills", "what skills are in my resume",
    )
    if any(phrase in q for phrase in resume_skill_phrases):
        items = "\n".join(f"- {skill}" for skill in resume_skills)
        return (
            f"**Resume skills detected ({len(resume_skills)}):**\n\n"
            f"{items or '- None detected'}"
        )

    jd_skill_phrases = (
        "job description skills", "jd skills", "required skills",
        "skills required by the job", "skills in the job description",
    )
    if any(phrase in q for phrase in jd_skill_phrases):
        items = "\n".join(f"- {skill}" for skill in jd_skills)
        return (
            f"**Job-description skills detected ({len(jd_skills)}):**\n\n"
            f"{items or '- None detected'}"
        )

    if "ats" in q or "checklist" in q:
        return format_ats_result(ats_result)

    return None


# ==========================================
# 9. CHAT HISTORY
# ==========================================

def build_chat_history():
    """Return recent conversation messages before the current question."""

    previous_messages = st.session_state.messages[:-1][-6:]

    if not previous_messages:
        return "No previous conversation."

    return "\n\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in previous_messages
    )


# ==========================================
# 10. GEMINI PROMPT
# ==========================================

def create_prompt(
    user_input,
    resume_context,
    jd_context,
    analysis_context,
    rag_context,
    web_context,
    chat_history,
):
    """Build a personalized prompt with strict accuracy rules."""

    return f"""
You are CareerRAG AI, a helpful career assistant for college
students and fresh graduates.

Use simple English suitable for a beginner.

RESUME CONTEXT:
{resume_context}

JOB DESCRIPTION CONTEXT:
{jd_context}

AUTHORITATIVE DASHBOARD ANALYSIS:
{analysis_context}

RETRIEVED CAREER KNOWLEDGE:
{rag_context}

WEB SEARCH RESULTS:
{web_context}

RECENT CHAT HISTORY:
{chat_history}

CURRENT USER QUESTION:
{user_input}

SKILL ACCURACY RULES:
1. The dashboard analysis is the source of truth for skill lists
   and the skill-match percentage.
2. Never recalculate or change the dashboard percentage.
3. Never move a skill between matching and missing lists.
4. Use the exact matching and missing lists when discussing them.
5. For learning roadmaps, prioritize the detected missing skills.
6. A missing skill means the analyzer did not detect it; it does
   not prove that the user cannot perform that skill.
7. Never claim the user has a skill unless the context supports it.
8. If analysis has not been run, explain that clearly.
9. The ATS checklist score is not a guarantee of passing an
   employer's ATS.

LEARNING ROADMAP RULES:
1. If the user asks for a roadmap, make it beginner-friendly.
2. Organize a 30-day roadmap into weeks and individual days when
   the user requests a 30-day plan.
3. Prioritize the exact missing skills from the dashboard.
4. For each day, include a topic, a practical task, and an
   expected outcome.
5. Include free learning resources and official documentation
   links when known and supported by retrieved results.
6. Use actual URLs from the provided web results. Never invent URLs.
7. If no verified link is available, provide the resource name and
   clearly say that the link was not verified.
8. Include hands-on practice and a realistic final portfolio project.
9. Assume a beginner studying approximately one hour per day unless
   the user gives a different schedule.
10. Describe 30 days as an introduction and practical foundation,
    not guaranteed mastery of every technology.

GENERAL RULES:
1. Answer the current question directly.
2. Use clear headings, lists, and practical examples.
3. Use retrieved knowledge when relevant.
4. Use web results for current information only when provided.
5. Never invent job openings, deadlines, qualifications, salary
   information, course links, or certification claims.
6. Clearly distinguish verified information from suggestions.
7. If information is unavailable or unverified, say so.
8. Use chat history to understand follow-up questions.
9. Do not repeat personal contact information unnecessarily.
10. Do not claim that a web search was performed if it was not.

Provide a clear, useful, personalized answer.
"""


# ==========================================
# 11. APP HEADER
# ==========================================

st.title("🎯 CareerRAG AI")

st.write("Your AI-powered Resume Analyzer and Career Assistant")

st.caption(
    "Analyze your resume, compare job requirements, "
    "check ATS basics, and ask career questions."
)


# ==========================================
# 12. SIDEBAR: UPLOADS AND CONTROLS
# ==========================================

with st.sidebar:
    st.header("📄 Upload Documents")

    resume_file = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx"],
        key="resume_uploader",
    )

    jd_file = st.file_uploader(
        "Upload job description (optional)",
        type=["pdf", "docx"],
        key="jd_uploader",
    )

    pasted_jd = st.text_area(
        "Or paste the job description",
        height=160,
        placeholder="Paste the job description here...",
    )

    analyze_button = st.button(
        "🔍 Analyze Resume",
        use_container_width=True,
        type="primary",
    )

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🔄 Clear Analysis", use_container_width=True):
        st.session_state.analysis = None
        st.rerun()


# ==========================================
# 13. PROCESS RESUME UPLOAD
# ==========================================

if resume_file is not None:
    current_hash = hashlib.sha256(
        resume_file.getvalue()
    ).hexdigest()

    if current_hash != st.session_state.resume_hash:
        try:
            with st.spinner("Extracting resume text..."):
                text, file_hash = extract_document_text(resume_file)

            st.session_state.resume_text = text
            st.session_state.resume_hash = file_hash
            st.session_state.resume_name = resume_file.name
            st.session_state.analysis = None

            if not text.strip():
                st.warning(
                    "No readable text was found in the resume. "
                    "A scanned PDF may require OCR."
                )

        except Exception as error:
            st.error(f"Could not read the resume: {error}")


# ==========================================
# 14. PROCESS JOB DESCRIPTION
# ==========================================

if jd_file is not None:
    current_jd_hash = hashlib.sha256(
        jd_file.getvalue()
    ).hexdigest()

    if current_jd_hash != st.session_state.jd_hash:
        try:
            with st.spinner("Extracting job description..."):
                jd_text, file_hash = extract_document_text(jd_file)

            st.session_state.jd_text = jd_text
            st.session_state.jd_hash = file_hash
            st.session_state.jd_name = jd_file.name
            st.session_state.analysis = None

        except Exception as error:
            st.error(f"Could not read the job description: {error}")

elif pasted_jd.strip():
    new_jd_text = pasted_jd.strip()

    if new_jd_text != st.session_state.jd_text:
        st.session_state.jd_text = new_jd_text
        st.session_state.jd_hash = hashlib.sha256(
            new_jd_text.encode("utf-8")
        ).hexdigest()
        st.session_state.jd_name = "Pasted job description"
        st.session_state.analysis = None

elif jd_file is None and not pasted_jd.strip():
    if st.session_state.jd_name == "Pasted job description":
        st.session_state.jd_text = ""
        st.session_state.jd_hash = ""
        st.session_state.jd_name = ""
        st.session_state.analysis = None


# ==========================================
# 15. DISPLAY DOCUMENT STATUS
# ==========================================

if st.session_state.resume_name:
    st.sidebar.success(
        f"Resume loaded: {st.session_state.resume_name}"
    )

if st.session_state.jd_name:
    st.sidebar.info(
        f"Job description loaded: {st.session_state.jd_name}"
    )

with st.expander("View extracted document text"):
    if st.session_state.resume_text:
        st.subheader("Resume text")
        st.text(st.session_state.resume_text[:12000])

    if st.session_state.jd_text:
        st.subheader("Job description text")
        st.text(st.session_state.jd_text[:8000])

    if not st.session_state.resume_text and not st.session_state.jd_text:
        st.info("Upload a document to view its extracted text.")


# ==========================================
# 16. ANALYZE RESUME AND JOB DESCRIPTION
# ==========================================

if analyze_button:
    if not st.session_state.resume_text.strip():
        st.warning("Please upload a readable resume first.")

    else:
        try:
            with st.spinner("Analyzing your resume..."):
                resume_text = st.session_state.resume_text
                jd_text = st.session_state.jd_text

                resume_skills = normalize_skills(
                    extract_skills(resume_text)
                )

                jd_skills = (
                    normalize_skills(extract_skills(jd_text))
                    if jd_text.strip()
                    else []
                )

                matching_skills, missing_skills = get_skill_comparison(
                    resume_skills,
                    jd_skills,
                )

                if jd_skills:
                    match_percentage = round(
                        len(matching_skills) / len(jd_skills) * 100,
                        2,
                    )
                else:
                    match_percentage = None

                ats_result = check_ats(resume_text, jd_text)

                st.session_state.analysis = {
                    "resume_skills": resume_skills,
                    "jd_skills": jd_skills,
                    "matching_skills": matching_skills,
                    "missing_skills": missing_skills,
                    "match_percentage": match_percentage,
                    "ats_result": ats_result,
                }

                # Reset the conversation after new analysis.
                st.session_state.messages = []

            st.success("Resume analysis completed!")

        except Exception as error:
            st.error(f"Resume analysis failed: {error}")


# ==========================================
# 17. DISPLAY ANALYSIS DASHBOARD
# ==========================================

analysis = st.session_state.analysis

if analysis is not None:
    st.divider()
    st.header("📊 Resume Analysis Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        if analysis["match_percentage"] is not None:
            st.metric(
                "Skill Match",
                f'{analysis["match_percentage"]}%',
            )
        else:
            st.metric("Skill Match", "N/A")
            st.caption("Add a job description to compare skills.")

    with col2:
        st.metric(
            "Matching Skills",
            len(analysis["matching_skills"]),
        )

    with col3:
        st.metric(
            "Missing Skills",
            len(analysis["missing_skills"]),
        )

    left, right = st.columns(2)

    with left:
        st.subheader("✅ Matching Skills")

        if analysis["matching_skills"]:
            for skill in analysis["matching_skills"]:
                st.write(f"- {skill}")
        else:
            st.info("No matching skills found yet.")

    with right:
        st.subheader("📌 Skills to Learn")

        if analysis["missing_skills"]:
            for skill in analysis["missing_skills"]:
                st.write(f"- {skill}")
        elif analysis["jd_skills"]:
            st.success("No missing skills detected.")
        else:
            st.info("Add a job description to identify missing skills.")

    with st.expander("View all detected resume skills"):
        st.write(analysis["resume_skills"])

    with st.expander("📋 View ATS checklist results", expanded=True):
        ats_result = analysis.get("ats_result", {})

        if isinstance(ats_result, dict):
            score = ats_result.get("score")
            status = ats_result.get("status")
            word_count = ats_result.get("word_count")

            metric1, metric2, metric3 = st.columns(3)

            with metric1:
                st.metric(
                    "ATS Checklist Score",
                    str(score) if score is not None else "N/A",
                )

            with metric2:
                st.metric(
                    "Resume Word Count",
                    str(word_count) if word_count is not None else "N/A",
                )

            with metric3:
                st.metric(
                    "ATS Status",
                    str(status) if status else "Not available",
                )

            checks = ats_result.get("checks", [])

            if checks:
                st.subheader("Individual Checks")

                for check in checks:
                    if not isinstance(check, dict):
                        st.write(check)
                        continue

                    check_name = check.get("check", "Unnamed check")
                    passed = check.get("passed", False)
                    details = check.get("details", "")

                    if passed:
                        st.success(f"✅ {check_name}: Passed")
                    else:
                        st.warning(
                            f"⚠️ {check_name}: Needs attention"
                        )

                    if details:
                        st.caption(str(details))

            missing_keywords = ats_result.get("missing_keywords", [])

            if missing_keywords:
                st.subheader("Missing ATS Keywords")
                st.write(", ".join(map(str, missing_keywords)))

            recommendations = ats_result.get("recommendations", [])

            if recommendations:
                st.subheader("Recommendations")

                if isinstance(recommendations, list):
                    for recommendation in recommendations:
                        st.write(f"- {recommendation}")
                else:
                    st.write(recommendations)

            known_keys = {
                "score",
                "status",
                "word_count",
                "checks",
                "missing_keywords",
                "recommendations",
            }

            other_fields = {
                key: value
                for key, value in ats_result.items()
                if key not in known_keys
            }

            if other_fields:
                st.markdown("**Other ATS details**")
                st.markdown(format_result(other_fields))

        else:
            st.write(ats_result)

    st.caption(
        "The skill match and ATS checklist are estimates, "
        "not a guarantee of passing an employer's ATS."
    )


# ==========================================
# 18. CAREER ASSISTANT CHAT
# ==========================================

st.divider()
st.header("💬 Career Assistant")

st.write(
    "Ask questions about your resume, missing skills, "
    "interview preparation, AI/ML learning, or career options."
)

# Display saved conversation.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Ask CareerRAG AI a question...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            # Dashboard facts come directly from Python.
            answer = answer_from_dashboard(user_input)

            if answer is None:
                with st.spinner("CareerRAG AI is preparing your answer..."):
                    resume_context = (
                        st.session_state.resume_text[:12000]
                        if st.session_state.resume_text
                        else "No resume has been uploaded."
                    )

                    jd_context = (
                        st.session_state.jd_text[:8000]
                        if st.session_state.jd_text
                        else "No job description has been provided."
                    )

                    analysis_context = build_analysis_context()

                    with st.spinner("Searching career knowledge..."):
                        retrieved_chunks = search_knowledge(
                            user_input,
                            top_k=3,
                        )

                    if retrieved_chunks:
                        rag_context = "\n\n".join(
                            str(chunk) for chunk in retrieved_chunks
                        )
                    else:
                        rag_context = "No relevant knowledge was retrieved."

                    web_context = (
                        "No web search was performed for this question."
                    )

                    if needs_web_search(user_input):
                        with st.spinner("Searching the web..."):
                            web_context = retrieve_web_context(user_input)

                    chat_history = build_chat_history()

                    prompt = create_prompt(
                        user_input=user_input,
                        resume_context=resume_context,
                        jd_context=jd_context,
                        analysis_context=analysis_context,
                        rag_context=rag_context,
                        web_context=web_context,
                        chat_history=chat_history,
                    )

                    answer = ask_gemini(prompt)

                    if not answer or not str(answer).strip():
                        answer = (
                            "I couldn't generate an answer this time. "
                            "Please try again."
                        )

                    answer = str(answer).strip()

            st.markdown(answer)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
            })

        except Exception as error:
            print(
                f"Career Assistant error: "
                f"{type(error).__name__}: {error}"
            )

            error_message = (
                "Sorry, I couldn't answer that question right now. "
                "Please try again in a moment. Check the terminal "
                "for technical details if the problem continues."
            )

            st.error(error_message)

            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message,
            })
