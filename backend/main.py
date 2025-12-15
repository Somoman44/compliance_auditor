from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import time
from langchain_groq import ChatGroq
import json
from fastapi import FastAPI, UploadFile, File, HTTPException,Body
import os
from dotenv import load_dotenv

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

def cleaner(docs):
    for doc in docs:
        # A. Replace multiple newlines with a single newline
        doc.page_content = re.sub(r'\n+', '\n', doc.page_content)
    
        # B. Replace multiple spaces/tabs with a single space
        doc.page_content = re.sub(r'\s+', ' ', doc.page_content)
    
        # C. Strip leading/trailing whitespace
        doc.page_content = doc.page_content.strip()
    return docs

template = """
You are an expert AI Compliance Auditor. Your task is to audit the USER DRAFT against the provided INTERNAL POLICY.

INTERNAL POLICY:
{context}

USER DRAFT:
{question}

INSTRUCTIONS:
1. **Violation Detection:** Analyze the draft strictly against the provided policy. If an action is compliant or not mentioned in the policy, IGNORE IT.
2. **Quantitative Logic:** If a rule defines a specific limit (e.g., currency, time, days, data size, count):
   - Compare the values in the draft against the limit.
   - If the value in the draft is within the allowed limit (<=), it is COMPLIANT. Do NOT flag it.
   - Only flag a violation if the limit is strictly violated.
3. **Contextual Adherence:** Do not apply general ethical standards or outside knowledge. Only enforce rules explicitly written in the INTERNAL POLICY section.
4. **Rule Extraction:** For the "violated_rule_id", extract the specific Section Number, Rule Number (e.g., "1.1"), or Header Name.
5. **Format:** Return a valid JSON object with a "violations" key.
6. If no violations are found, return exactly: {{ "violations": [] }}
7. Do not include more than 2 violations per chunk.

OUTPUT FORMAT:
{{
  "violations": [
    {{
      "violated_rule_id": "1.1",
      "violated_rule_text": "Exact text of the rule...",
      "reasoning": "Concise explanation of the violation..."
    }}
  ]
}}
"""

app = FastAPI()
@app.post("/policy")
async def upload_policy(file: UploadFile = File(...)):
    try:
        content = file.file.read().decode("utf-8")
        with open("./data/policy.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        loader = TextLoader('./data/policy.txt')
        document = loader.load()
        document = cleaner(document)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=350,
            chunk_overlap=70
            )
        texts = text_splitter.split_documents(document)

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key
            )
        
        policy_store = None

        policy_store = Chroma.from_documents(
            documents = texts,
            embedding=embeddings,
        )

        app.state.policy_store = policy_store

        return {"message": "Policy document uploaded and processed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check_compliance")
async def check_compliance(s: str =Body(..., embed = True)):
    try:
        policy_store = app.state.policy_store

        if not policy_store:
            raise HTTPException(status_code=400, detail="Policy document not uploaded. Please upload a policy document first.")

        prompt = ChatPromptTemplate.from_template(template)

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key,
            temperature=0,
            max_tokens=500,
            timeout=None,
            max_retries=2,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

        retriver = policy_store.as_retriever(search_kwargs={"k":3})

        rag_chain = (
            {"context": retriver, "question":RunnablePassthrough()}
            |prompt
            |llm
            |StrOutputParser()
        )

        result = rag_chain.invoke(s)
        return json.loads(result)
    except Exception as e:
        return {"violations": [], "error": str(e)}
    
@app.post("/delete")
async def delete_policy():
    try:
        app.state.policy_store = None
        return {"message": "Policy document deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))