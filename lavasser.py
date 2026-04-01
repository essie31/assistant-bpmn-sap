import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import time

# --- Configuration de la page ---
st.set_page_config(page_title="App 1 : Analyse & Architecture SAP", page_icon="📊", layout="wide")

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
    
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.title("🚀 Navigation")
        st.link_button("💬 Assistant de Configuration (App 2)", "https://votre-app-chat.streamlit.app")
        st.divider()
        st.write("Moteur : Gemini 1.5 Pro")

    # ==========================================
    # 🔑 CONFIGURATION GOOGLE
    # ==========================================
    try:
        API_KEY = st.secrets["API_KEY"] 
        client = genai.Client(api_key=API_KEY)
        MODEL_NAME = 'gemini-1.5-pro'
    except Exception as e:
        st.error("Erreur de configuration de la clé API. Vérifiez vos secrets Streamlit.")

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
                    elements[e_id] = {'name': e_name}
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
        Tu es un Architecte Senior SAP Business One 10.0. 
        TÂCHES : {tasks}
        FLUX : {flows}

        Génère un rapport d'architecture technique exhaustif avec :
        1. 📊 Tableau des Tâches & Rôles.
        2. 📝 Analyse Logique & Métier (4 paragraphes minimum).
        3. 🔵 Architecture SAP B1 10.0 (Objet Technique, Chemin Menu, Données Maîtres et Impact Stock/Compta).
        """
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=8192)
            )
            return response.text
        except Exception as e:
            # Gestion spécifique de l'erreur de quota (Rate Limit)
            if "429" in str(e) or "quota" in str(e).lower():
                return "⚠️ L'API est surchargée. Veuillez attendre 30 secondes et cliquer à nouveau sur le bouton."
            else:
                return f"❌ Erreur lors de la génération : {str(e)}"

    # ==========================================
    # 🏁 UI PRINCIPALE
    # ==========================================
    st.title("🏭 Hub d'Analyse Métier ➔ Architecture SAP B1")
    uploaded_file = st.file_uploader("Fichier .bpmn ou .xml", type=['bpmn', 'xml'])

    if uploaded_file:
        if st.button("🚀 Générer l'Analyse & Intégration SAP", type="primary"):
            with st.spinner("L'IA analyse votre processus..."):
                tasks_txt, flows_txt = parse_bpmn_from_file(uploaded_file)
                if tasks_txt:
                    report = generate_detailed_analysis(tasks_txt, flows_txt)
                    if report.startswith("⚠️") or report.startswith("❌"):
                        st.warning(report)
                    else:
                        st.success("Rapport généré !")
                        st.markdown(report)
                else:
                    st.error("Fichier BPMN invalide.")
