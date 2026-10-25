import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load API key from .env
load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError("TAVILY_API_KEY is missing from .env")

# Connect to Tavily
tavily = TavilyClient(api_key=api_key)


def search_web(query):
    response = tavily.search(
        query=query,
        search_depth="basic",
        max_results=5
    )

    return response.get("results", [])