import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page ---
st.set_page_config(page_title="Hub BPMN ➔ SAP (Analyse)", page_icon="📊", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container { height: auto !important; overflow: visible !important; display: block !important; position: relative !important; }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput { display: none !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; }
    tr { page-break-inside: avoid; page-break-after: auto; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SÉCURITÉ
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"] 

def check_password():
    def password_entered():
        if st.session_state["password"] == CODE_SECRET:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        st.text_input("Code d'accès :", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Accès Restreint")
        st.text_input("Code d'accès :", type="password", on_change=password_entered, key="password")
        st.error("😕 Code d'accès incorrect.")
        return False
    return True

if check_password():
    
    # --- LIEN VERS L'APP 2 DANS LA SIDEBAR ---
    with st.sidebar:
        st.title("🚀 Navigation")
        st.info("Besoin d'aide pour la configuration ?")
        # Remplacez par votre vrai lien une fois l'App 2 déployée
        st.link_button("💬 Aller à l'Assistant Chat SAP", "https://votre-deuxieme-app.streamlit.app")
        st.divider()
        st.write("Modèle : Gemini 2.5 Flash")

    # ==========================================
    # 🔑 CONFIGURATION GOOGLE
    # ==========================================
    API_KEY = st.secrets["API_KEY"] 
    client = genai.Client(api_key=API_KEY)
    MODEL_NAME = 'gemini-2.5-flash'

    def parse_bpmn_from_file(file_object):
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
            lane_map = {node_ref.text: lane.get('name', 'Général') 
                        for lane in root.findall('.//bpmn:lane', ns) 
                        for node_ref in lane.findall('bpmn:flowNodeRef', ns)}
            
            tasks = []
            flows = []
            elements = {}

            for elem in root.findall('.//bpmn:process/*', ns):
                if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                    e_id, e_name = elem.get('id'), elem.get('name', 'Sans nom').strip()
                    e_type = elem.tag.split('}')[-1]
                    lane = lane_map.get(e_id, 'Général')
                    elements[e_id] = {'name': e_name, 'lane': lane}
                    if e_name != 'Sans nom':
                        tasks.append(f"- [{lane}] {e_name} ({e_type})")

            for flow in root.findall('.//bpmn:sequenceFlow', ns):
                src, tgt = flow.get('sourceRef'), flow.get('targetRef')
                if src in elements and tgt in elements:
                    flows.append(f"De '{elements[src]['name']}' vers '{elements[tgt]['name']}'")

            return "\n".join(tasks), "\n".join(flows)
        except: return None, None

    def generate_full_analysis(tasks_text, flows_text):
        prompt = f"""
        Tu es un Architecte SAP Senior et Expert Industrie 4.0. Analyse ce processus :
        
        TÂCHES : {tasks_text}
        FLUX : {flows_text}

        Génère un rapport de haute qualité avec :

        ### 1. 📊 Architecture & Intégration SAP B1 10.0 (Ultra-Détaillé)
        Pour chaque tâche informatisable, fournis :
        * **Tâche :** [Nom]
        * **Module & Objet SAP :** [Ex: Production - OWOR]
        * **Action Technique :** [Description précise des champs et de l'impact transactionnel (OIGN/OIGE)]
        * **Impact Stock/Compta :** [Impact sur les tables OITW et OJDT]

        ### 2. 🏭 Matrice de Maturité Industrie 4.0
        Génère UN SEUL grand tableau Markdown évaluant TOUTES les tâches sur les 9 piliers.
        Colonnes : Tâche | Big Data | Robots | Simul | Intégr | IIoT | Cyber | Cloud | Additif | RA | Justification.

        ### 3. SCORES_JSON
        Moyenne globale 1-5 pour le radar.
        ```json
        {{ "Big Data": 0, "Robots Autonomes": 0, "Simulation": 0, "Intégration Systèmes": 0, "IIoT": 0, "Cybersécurité": 0, "Cloud": 0, "Fabrication Additive": 0, "Réalité Augmentée": 0 }}
        ```
        """
        response = client.models.generate_content(
            model=MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=8192)
        )
        return response.text

    # ==========================================
    # 🏁 UI PRINCIPALE
    # ==========================================
    st.title("🏭 Hub d'Architecture : BPMN ➔ SAP B1")
    uploaded_file = st.file_uploader("Importez votre BPMN (.bpmn, .xml)", type=['bpmn', 'xml'])

    if uploaded_file:
        if st.button("🚀 Lancer l'Analyse Métier & 4.0", type="primary"):
            with st.spinner("Analyse approfondie en cours..."):
                t_txt, f_txt = parse_bpmn_from_file(uploaded_file)
                report = generate_full_analysis(t_txt, f_txt)
                
                # Extraction Radar
                json_match = re.search(r'```json\n(.*?)\n```', report, re.DOTALL)
                clean_report = re.sub(r'### 3\. SCORES_JSON.*', '', report, flags=re.DOTALL)
                
                col_text, col_radar = st.columns([2, 1])
                with col_text:
                    st.markdown(clean_report)
                
                with col_radar:
                    if json_match:
                        st.subheader("📈 Radar de Maturité")
                        scores = json.loads(json_match.group(1))
                        df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
                        fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5])
                        fig.update_traces(fill='toself', line_color='#ff7f0e')
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(pd.DataFrame(list(scores.items()), columns=['Pilier', 'Note']), hide_index=True)
