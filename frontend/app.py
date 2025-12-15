import streamlit as st
import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utilis import cleaner1

st.set_page_config(page_title="Compliance Auditor", layout="wide")

st.title("Compliance Auditor")

with st.sidebar:
    st.title('Policy File(TXT)')
    uploaded_file = st.file_uploader("upload policy text file here")
    if uploaded_file and "uploaded" not in st.session_state:
        with st.spinner("Uploading policy",show_time=True):
            files = {'file': uploaded_file.getvalue()}
            try:
                response = requests.post("http://127.0.0.1:8000/policy", files=files)
                if response.status_code == 200:
                    st.session_state.uploaded = True
                    st.session_state.policy_text = uploaded_file.getvalue().decode('utf-8')
                    st.success("Policy Active")
            except Exception as e:
                st.error(f"Connection Error: {e}")

st.session_state.draft = None
submit = False


with st.form("Draft"):
    st.write("enter you draft here")
    draft_input = st.text_area("")
    submit = st.form_submit_button("Submit")
    if submit:
        st.session_state.draft = draft_input


if uploaded_file is not None:

    if st.session_state.draft is not None:
        
        #body = {'s': draft}
        #response = requests.post("http://127.0.0.1:8000/check_compliance", json=body)
        #st.write(response.json())
        
        with st.spinner("Analysing draft"):
            text_splitter = RecursiveCharacterTextSplitter(separators=["\n"],chunk_size=200,chunk_overlap=40)
            docs = text_splitter.split_text(st.session_state.draft)
            docs = cleaner1(docs)
            result = []
            for num,doc in enumerate(docs,1):
                body = {'s': doc}
                response1 = requests.post("http://127.0.0.1:8000/check_compliance", json=body)
                result.append(response1.json())

            total = max(len(result),1)
            violations = 0
            for i in result:
                if i['violations']:
                    violations += 1
            score = round((1 - (violations/total))*100,2)
            #st.metric(label='Compliance Score',value=compliance_score)

            st.divider()
            col1, col2 = st.columns([1, 4])
                
            with col1:
                # Color-coded metric
                delta_color = "normal" if score == 100 else "inverse"
                st.metric(
                    label="Compliance Score", 
                    value=f"{score}/100", 
                    delta=f"-{violations} Violations" if (violations>0) else "Perfect",
                    delta_color=delta_color
                )
                
            with col2:
                st.write("### Audit Status")
                if score == 100:
                    st.progress(1.0, text="✅ Fully Compliant")
                elif score > 50:
                    st.progress(score/100, text="⚠️ Risks Detected")
                else:
                    st.progress(score/100, text="🚨 Critical Failures")
            
            st.subheader("📝 Detailed Findings")
            for i in range(len(result)):

                st.write(docs[i])

                if not result[i]["violations"]:
                    st.success("No violations found in this paragraph.")

                else:
                    for violations in result[i]["violations"]:
                        

                        rule_id = violations["violated_rule_id"]
                        rule_text = violations["violated_rule_text"]
                        reasoning = violations["reasoning"]
            
                        with st.expander(f"🚨 Violation #{i+1}: Rule {rule_id}", expanded=True):
                            
                            c1, c2 = st.columns([1, 1])
                            
                            with c1:
                                st.markdown("**🔍 AI Reasoning:**")
                                st.error(reasoning) # Red box for the bad news
                                
                            with c2:
                                st.markdown("**📖 Policy Reference:**")
                                st.info(f"_{rule_text}_")




elif uploaded_file is None:
    requests.post("http://127.0.0.1:8000/delete")
    if st.session_state.draft is not None:
        st.write('upload policy first!!')