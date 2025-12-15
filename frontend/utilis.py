import re
def cleaner1(docs):
    for doc in docs:
        # A. Replace multiple newlines with a single newline
        doc = re.sub(r'\n+', '\n', doc)
    
        # B. Replace multiple spaces/tabs with a single space
        doc = re.sub(r'\s+', ' ', doc)
    
        # C. Strip leading/trailing whitespace
        doc = doc.strip()
    return docs