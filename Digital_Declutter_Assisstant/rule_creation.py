import requests
import json
# Ask Mistral via Ollama's REST API
def ask_model(prompt):
    try:
        response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    
    except requests.exceptions.Timeout:
        print("Ollama response timed out - try simpler rule descriptions")
        return None
    
def create_rule_from_natural_language(user_input):
    """Convert natural language to structured rule"""
    prompt = f"""Convert this natural language instruction to ONE JSON rule:
    "{user_input}"
    
    OUTPUT FORMAT, ENSURE PROPER JSON FORMATTING (ONLY ONE RULE):
    {{
        "condition": "source_category == '...'" or "source_category != '...'" or "filetype == '...'",
        "action": {{
            "type": "move/delete/copy",
            "target_path": "absolute path from C:/Users/g6msd/OneDrive/Pictures/Screenshots", // if move/copy
            "time": "X days/hours"        // if delete
        }},
        "priority": <one source_category condition is 1 point, a filetype condition is 2 points>
    }}
    Output ONLY the JSON, no explanations."""
    

    raw_output = ask_model(prompt)
        
        # Extract JSON from markdown code blocks if present
    if '```' in raw_output:
        raw_output = raw_output.split('``````')[0]
            
    print(raw_output)
    return json.loads(raw_output)