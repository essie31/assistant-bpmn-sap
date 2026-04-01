import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import time

# --- Configuration de la page ---
st.set_page_config(page_title="App 1 : Analyse & Architecture SAP", page_icon="📊", layout="wide")

# ==========================================
# 🔒 SÉCURITÉ & ACCÈS
# ==========================================
if "password_correct" not in st.session_state:
    st.title("🔒 Accès Restreint")
    pwd = st.text_input("Veuillez entrer le code d'accès :", type="password")
    if st.button("Valider"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Code d'accès incorrect.")
    st.stop()

# ==========================================
# 🔑 CONFIGURATION GOOGLE (ANTI-ERREUR)
# ==========================================
API_KEY = st.secrets["API_KEY"] 
client = genai.Client(api_key=API_KEY)
# On utilise la version 1.5 Flash qui est plus stable sur les quotas gratuits que la 2.0
MODEL_NAME = 'gemini-1.5-flash' 

def parse_bpmn_minimal(file_object):
    """Extrait uniquement l'essentiel pour économiser le quota de jetons."""
    try:
        tree = ET.parse(file_object)
        root = tree.getroot()
        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        tasks = []
        for elem in root.findall('.//bpmn:task', ns):
            name = elem.get('name')
            if name: tasks.append(name.strip())
        return "\n".join(tasks)
    except: return None

def generate_with_retry(prompt, retries=3):
    """Tente de générer le contenu et attend si le quota est dépassé."""
    for i in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            return response.text
        except Exception as e:
            if "429" in str(e) and i < retries - 1:
                time.sleep(15) # Attend 15 secondes avant de réessayer
                continue
            return f"⚠️ Erreur de quota : Veuillez attendre 1 minute. (Détail : {str(e)})"

# ==========================================
# 🏁 INTERFACE UTILISATEUR
# ==========================================
st.title("🏭 Hub d'Architecture SAP Business One")
st.sidebar.link_button("💬 Aller vers l'Assistant Chat (App 2)", "https://votre-app-chat.streamlit.app")

uploaded_file = st.file_uploader("Charger le fichier .bpmn", type=['bpmn', 'xml'])

if uploaded_file:
    tasks_txt = parse_bpmn_minimal(uploaded_file)
    
    if st.button("🚀 Générer l'Analyse SAP", type="primary"):
        with st.spinner("Analyse approfondie en cours..."):
            # Prompt ultra-précis basé sur vos corrections
            full_prompt = f"""
            Tu es un Architecte Senior SAP B1 10.0. Analyse ces tâches :
            {tasks_txt}

            Génère un rapport exhaustif avec ces règles strictes :
            1. 📊 Tableau Synthétique (Département | Tâche).
            2. 📝 Analyse Métier détaillée (4 paragraphes).
            3. 🔵 Architecture SAP B1 10.0 :
               - Utilise l'objet OIGN (Déclaration de production) pour les étapes de traitement.
               - Utilise ODLN (Livraison) pour l'export.
               - Précise les tables (OITW, OJDT) et les impacts réels.
            """
            
            report = generate_with_retry(full_prompt)
            st.markdown(report)
