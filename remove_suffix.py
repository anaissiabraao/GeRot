
import os

file_path = r"c:\Users\Dell\GeRot\app_production.py"
target_string = 'ai_response = response.text + "\\n\\n*(Gerado via Gemini - Fallback)*"'
replacement_string = 'ai_response = response.text'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if target_string in content:
        new_content = content.replace(target_string, replacement_string)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully replaced the string.")
    else:
        print("Target string not found.")
        # Debug: print context around where it should be
        idx = content.find("response = model.generate_content(full_prompt)")
        if idx != -1:
            print("Context found:")
            print(content[idx:idx+200])

except Exception as e:
    print(f"Error: {e}")
