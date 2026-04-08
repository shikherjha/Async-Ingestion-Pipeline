import asyncio
from backend.llm import extract

text = "Hiring at TechCorp for Junior Developer, batch 2025, stipend 50000/month, San Francisco. Apply at careers.techcorp.com"

print("testing LLM extraction...")
try:
    result, provider = extract(text)
    print(f"Provider used: {provider}")
    print(f"Extracted json: {result}")
except Exception as e:
    print(f"Error: {e}")
