import re
import json

def parse_markdown_to_qa(file_path):
    qa_list = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by headers (e.g., #### 1.1 Historia...)
    # We look for sections starting with #### X.X or ### 
    # Regex to capture Section Title and Content
    # We focus on "Capítulo I: Ciencia" and "Capítulo II: Tecnología" content.
    
    # Extract Chapter 1 and 2 roughly
    science_start = content.find("Fundamentación Científica del Modelo")
    tech_start = content.find("Fundamentación Tecnológica (Capítulo II")
    
    if science_start == -1: return []
    
    relevant_content = content[science_start:] # From Science onwards

    # Pattern: #### Title \n Content
    # We'll split by "#### "
    sections = relevant_content.split('#### ')
    
    for section in sections[1:]: # Skip preamble
        lines = section.split('\n')
        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()
        
        # Clean up body
        # Remove page numbers, huge gaps
        body = re.sub(r'\n\d+\n', '', body) # Remove page numbers like "72" on a line
        body = re.sub(r'\n\s*\n', '\n', body) # Remove extra newlines
        
        if len(body) > 50:
            qa_item = {
                "category": "Bluebook Science & Tech",
                "question": f"Explícame sobre: {title}",
                "answer": body[:1000], # Limit length for context window
                "keywords": title.lower().split()
            }
            qa_list.append(qa_item)
            
            # Create extra specific QAs if possible?
            # For now, section-based is good for RAG.
            
    return qa_list

# Source and Target
source = "/Users/yepz/Desktop/Bluebook Project/TESIS/Tesis_Integrada.md"
target = "/Users/yepz/Desktop/Bluebook Project/bluechat/qa-data/bluebook.json"

data = parse_markdown_to_qa(source)

with open(target, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {len(data)} items in {target}")
