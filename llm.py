from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

def call_gemini(prompt: str, model_name: str):
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.getenv("Gemini_api_key")
    )

    response = llm.invoke(prompt)
    return response
