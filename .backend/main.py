import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyB8YWnoZe-Ry3_eFp8yYlvRCgd6_aY1YoA")
model = genai.GenerativeModel("models/gemini-2.5-flash")


def get_gemini_response(query: str) -> str:
    """
    Send a query to Gemini and return the response text.
    
    Args:
        query: The user's query string
        
    Returns:
        The Gemini response text
        
    Raises:
        Exception: If there's an error generating the response
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    print(f"Processing query: {query}")
    
    # Send query to Gemini
    response = model.generate_content(query)
    
    # Extract the text from the response
    gemini_output = response.text
    
    print(f"Gemini response received: {len(gemini_output)} characters")
    
    return gemini_output