from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You convert user questions into Prometheus queries.

STRICT RULES:
- Return ONLY the query
- No explanation
- No extra text

Available metrics:
- orders_processed_total
- high_value_orders_total

Example:
Q: high value orders per minute
A: rate(high_value_orders_total[1m])
"""

def get_query_from_llm(question):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("LLM ERROR:", str(e))

        # fallback
        if "high value" in question:
            return "rate(high_value_orders_total[1m])"
        return "rate(orders_processed_total[1m])"