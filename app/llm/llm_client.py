from google import genai
from google.genai import types

from app.llm.regulatory_prompt import REGULATORY_SYSTEM_PROMPT


# Initialize the Gemini client
client = genai.Client()


# Function to send a regulatory question to Gemini
def ask_llm(question):

    # Send the question with regulatory instructions
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=REGULATORY_SYSTEM_PROMPT,
            temperature=0.2
        )
    )

    # Return the generated response
    return response.text