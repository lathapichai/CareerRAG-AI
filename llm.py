
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. Check your .env file."
    )

client = genai.Client(api_key=API_KEY)


def ask_gemini(prompt):
    """Send a prompt to Gemini with limited retries."""

    if not isinstance(prompt, str) or not prompt.strip():
        return "Please enter a valid question."

    max_attempts = 5

    for attempt in range(max_attempts):
        try:
            print(
                f"Connecting to Gemini model {MODEL} "
                f"(attempt {attempt + 1}/{max_attempts})..."
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            answer = response.text

            if answer and answer.strip():
                print("Gemini response received.")
                return answer.strip()

            print("Gemini returned an empty response.")
            return "Gemini returned no text. Please try again."

        except errors.APIError as e:
            # Google Gen AI SDK API errors expose a status code.
            status = getattr(e, "code", None)
            message = str(e)

            print(f"Gemini API error: status={status}, {message}")

            # Retry temporary service and rate-limit errors.
            if status in (429, 500, 502, 503, 504):
                if attempt < max_attempts - 1:
                    wait_seconds = 2 ** (attempt + 1)
                    print(f"Retrying in {wait_seconds} seconds...")
                    time.sleep(wait_seconds)
                    continue

                if status == 429:
                    return (
                        "Gemini API quota or rate limit reached. "
                        "Check your API usage and limits."
                    )

                return (
                    f"Gemini service is temporarily unavailable "
                    f"(HTTP {status}). Please try again later."
                )

            if status in (400, 401, 403, 404):
                return (
                    f"Gemini API request failed (HTTP {status}). "
                    "Check the model name, API key, and API access. "
                    "See the terminal for diagnostic details."
                )

            return (
                f"Gemini API request failed (HTTP {status}). "
                "Check the terminal for diagnostic details."
            )

        except Exception as e:
            print(
                f"Unexpected Gemini error: "
                f"{type(e).__name__}: {e}"
            )

            if attempt < max_attempts - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            return (
                "Could not connect to Gemini after 3 attempts. "
                "Check your internet connection and terminal output."
            )

    return "Unable to get a response from Gemini."
