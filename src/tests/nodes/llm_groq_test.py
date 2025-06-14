import os
from groq import Groq

def query_groq(prompt: str, model: str = "deepseek-r1-distill-llama-70b", temperature: float = 0.6, max_tokens: int = 1024):
    """Test Groq API with a single prompt"""
    try:
        client = Groq(api_key="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")
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"API Error: {str(e)}"

if __name__ == "__main__":
    
    test_prompt = """Analyze this typing data for patterns:
    Sample data: ["w","w","a","s","w","d","d","shift","g"]
    
    Identify which activity the user is performing.
    Return only JSON in this format without any additional text:
    {
        "activity": 
        "description": 
    }
    """
    
    print("Testing Groq API...\n")
    print("Prompt:", test_prompt[:200] + "...\n")  # Show first 200 chars
    
    result = query_groq(
        prompt=test_prompt,
        model="llama3-70b-8192",
        temperature=0.5,
        max_tokens=1000
    )
    
    print("\nAPI Response:")
    print(result)