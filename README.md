# CareerRAG AI — RAG-Powered Resume & Career Assistant

CareerRAG AI is an AI-powered web application that helps job seekers analyze their resumes against job descriptions, identify missing skills, evaluate resume readiness, and receive personalized career guidance.

## Features

- **Resume Analysis:** Upload and extract text from resumes.
- **Job Description Analysis:** Compare resume skills with job requirements.
- **Skill Gap Analysis:** Identify matching and missing skills.
- **ATS Checker:** Evaluate resume readiness and identify areas for improvement.
- **AI Career Assistant:** Ask questions about resumes, skills, interviews, and career development.
- **Personalized Learning Roadmaps:** Get structured learning plans for missing skills.
- **Interview Preparation:** Generate technical interview practice questions.
- **Web Resource Search:** Find relevant learning resources using web search.
- **Context-Aware Responses:** Use resume and job-description context to provide relevant answers.

## Technologies Used

- Python
- Streamlit
- Generative AI — Gemini API
- Retrieval-Augmented Generation (RAG)
- FAISS
- Sentence Transformers
- Natural Language Processing (NLP)
- PyMuPDF
- python-docx
- Tavily API
- Python dotenv

## Project Structure

```text
CareerPilotAI/
├── app.py
├── analyzer.py
├── ats_checker.py
├── resume_parser.py
├── llm.py
├── rag.py
├── web_search.py
├── uploads/
├── requirements.txt
├── .env
└── README.md
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd CareerPilotAI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a local `.env` file in the project root and configure your API credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_supported_gemini_model
TAVILY_API_KEY=your_tavily_api_key
```

Replace the example values with your own credentials. Do not commit API keys or the `.env` file to GitHub.

### 6. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL displayed in the terminal.

## How It Works

1. Upload a resume and provide a job description.
2. Extract text and analyze relevant skills.
3. Compare resume skills against job requirements.
4. Display matching skills, missing skills, and a match percentage.
5. Evaluate resume readiness using ATS checks.
6. Ask the AI Career Assistant for learning guidance, interview preparation, and career advice.
7. Retrieve relevant web resources when needed.

## Security

- Keep API credentials private.
- Exclude `.env`, virtual environments, and personal resume files from version control.
- Do not upload confidential personal information or test resumes without permission.

## Future Improvements

- Improve skill synonym detection and matching accuracy.
- Add resume improvement suggestions.
- Expand AI/ML career learning pathways.
- Improve automated testing and error handling.
- Deploy the application for public access.

## Author

Developed as an AI-powered career assistance project using Python, Generative AI, and NLP.
