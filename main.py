from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import time

from db import user_collection, logs_collection
from genai_llm import call_gemini
app = FastAPI()

GEMINI_PRICING = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
}


class InitRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


class PromptRequest(BaseModel):
    email: EmailStr
    prompt: str = Field(..., min_length=1)
    model_name: str


class PromptResponse(BaseModel):
    response: str
    prompt_tokens: int
    response_tokens: int
    total_tokens: int
    estimated_cost: float


def calculate_cost(model_name: str, prompt_tokens: int, response_tokens: int) -> float:
    pricing = GEMINI_PRICING[model_name]
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (response_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


@app.post("/init_user")
async def init_user(data: InitRequest):
    existing = user_collection.find_one({"email": data.email})
    if existing:
        return {"message": "User already exists", "email": data.email}

    user_doc = {
        "name": data.name,
        "email": data.email,
        "created_at": datetime.utcnow(),
    }
    user_collection.insert_one(user_doc)
    return {"message": "New user created", "email": data.email}


@app.post("/ask", response_model=PromptResponse)
async def ask_llm(data: PromptRequest):
    # Check model name
    if data.model_name not in GEMINI_PRICING:
        raise HTTPException(status_code=400, detail="Invalid model name")

    # Ensure user exists
    user = user_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_time = time.time()

    try:
        # Call Gemini
        response = call_gemini(data.prompt, data.model_name)
        response_text = response.text

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = usage.prompt_token_count if usage else 0
        response_tokens = usage.candidates_token_count if usage else 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Provider Error: {str(e)}")

    total_tokens = prompt_tokens + response_tokens
    estimated_cost = calculate_cost(data.model_name, prompt_tokens, response_tokens)
    latency = time.time() - start_time

    # Log to MongoDB
    logs_collection.insert_one(
        {
            "user_id": user["_id"],
            "email": user["email"],
            "model_name": data.model_name,
            "prompt": data.prompt,
            "response": response_text,
            "usage": {
                "prompt": prompt_tokens,
                "completion": response_tokens,
                "total": total_tokens,
            },
            "cost": estimated_cost,
            "latency": round(latency, 3),
            "created_at": datetime.utcnow(),
        }
    )

    return {
        "response": response_text,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
    }
