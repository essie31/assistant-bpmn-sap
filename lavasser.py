import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import pandas as pd

# --- Configuration de la page ---
st.set_page_config(page_title="App 1 : Analyse & Architecture SAP", page_icon="📊", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION (CTRL+P)
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container { height: auto !important; overflow: visible !important; display: block !important; position: relative !important; }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput { display: none !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; font-size: 12px; }
    tr { page-break-inside: avoid; page-break-after: auto; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"] 

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        pwd = st.text_input("Veuillez entrer le code d'accès :", type="password")
        if st.button("Valider"):
            if pwd == CODE_SECRET:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("😕 Code d'accès incorrect.")
        return False
    return True

if check_password():
    
    # --- BARRE LATÉRALE DE NAVIGATION ---
    with st.sidebar:
        st.title("🚀 Navigation")
        st.info("Besoin d'aide pour configurer SAP ?")
        # Remplacez par le lien de votre App 2 (Assistant Chat)
        st.link_button("💬 Assistant de Configuration (App 2)", "https://votre-app-chat.streamlit.app")
        st.divider()
        st.write("Modèle : Gemini 1.5 Pro")

    # ==========================================
    # 🔑 CONFIGURATION GOOGLE GEMINI
    # ==========================================
    API_KEY = st.secrets["API_KEY"] 
    client = genai.Client(api_key=API_KEY)
    MODEL_NAME = 'gemini-1.5-pro'

    def parse_bpmn_from_file(file_object):
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
            lane_map = {node_ref.text: lane.get('name', 'Général') 
                        for lane in root.findall('.//bpmn:lane', ns) 
                        for node_ref in lane.findall('bpmn:flowNodeRef', ns)}
            
            tasks, flows, elements = [], [], {}

            for elem in root.findall('.//bpmn:process/*', ns):
                if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                    e_id, e_name = elem.get('id'), elem.get('name', 'Sans nom').strip()
                    lane = lane_map.get(e_id, 'Général')
                    elements[e_id] = {'name': e_name, 'lane': lane}
                    if e_name != 'Sans nom':
                        tasks.append(f"- [{lane}] {e_name}")

            for flow in root.findall('.//bpmn:sequenceFlow', ns):
                src, tgt = flow.get('sourceRef'), flow.get('targetRef')
                if src in elements and tgt in elements:
                    flows.append(f"'{elements[src]['name']}' ➔ '{elements[tgt]['name']}'")

            return "\n".join(tasks), "\n".join(flows)
        except: return None, None

    def generate_detailed_analysis(tasks, flows):
        prompt = f"""
        Tu es un Architecte Senior SAP Business One 10.0. Analyse ce processus industriel :
        
        TÂCHES : {tasks}
        FLUX : {flows}

        Génère un rapport d'architecture technique exhaustif :

        ### 1. 📊 Tableau des Tâches & Rôles
        Dresse un tableau Markdown (Département | Tâche BPMN).

        ### 2. 📝 Analyse Logique & Métier
        Analyse approfondie (minimum 4 paragraphes). Explique la circulation des flux, les points critiques de contrôle qualité et la logique de production de bout en bout.

        ### 3. 🔵 Intégration & Architecture SAP B1 10.0 (Ultra-Détaillé)
        Pour chaque tâche informatisable, fournis une documentation d'implémentation senior :
        * **Tâche :** [Nom]
        * **Objet Technique SAP :** [Ex: Étape de route dans OF (OWOR) / Déclaration (OIGN) / Livraison (ODLN)]
        * **Chemin Menu Standard :** [Chemin exact dans SAP B1 10.0]
        * **Données Maîtres (Master Data) :** [Nomenclatures, Articles, Ressources ou Partenaires requis]
        * **Détail de l'Action & Impact :** [Description précise des champs à remplir et impact sur les tables OITW (Stock) et OJDT (Comptabilité)]
        * **Note de personnalisation :** [Propose un UDF si le standard est incomplet]
        """
        response = client.models.generate_content(
            model=MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=8192)
        )
        return response.text

    # ==========================================
    # 🏁 UI PRINCIPALE
    # ==========================================
    st.title("🏭 Hub d'Analyse Métier ➔ Architecture SAP B1")
    st.write("Importez votre fichier BPMN pour générer le rapport d'implémentation technique.")
    
    uploaded_file = st.file_uploader("Fichier .bpmn ou .xml", type=['bpmn', 'xml'])

    if uploaded_file:
        if st.button("🚀 Générer l'Analyse & Intégration SAP", type="primary"):
            with st.spinner("L'architecte senior rédige votre rapport (Gemini 1.5 Pro)..."):
                tasks_txt, flows_txt = parse_bpmn_from_file(uploaded_file)
                if tasks_txt:
                    report = generate_detailed_analysis(tasks_txt, flows_txt)
                    st.success("Rapport généré avec succès. Vous pouvez l'imprimer avec Ctrl+P.")
                    st.divider()
                    st.markdown(report)
                else:
                    st.error("Impossible d'analyser le fichier. Vérifiez le format BPMN.")
