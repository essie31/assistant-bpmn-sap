import streamlit as st
import xml.etree.ElementTree as ET
from groq import Groq

# --- Configuration de la page ---
st.set_page_config(page_title="App 1 : Architecture SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION (CTRL+P)
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container {
        height: auto !important;
        overflow: visible !important;
        display: block !important;
        position: relative !important;
    }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput, .stChatInputContainer {
        display: none !important;
    }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SÉCURITÉ
# ==========================================
CODE_SECRET = st.secrets["APP_PASSWORD"] if "APP_PASSWORD" in st.secrets else "LAVASSER2026"

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Accès Restreint")
        pwd = st.text_input("Veuillez entrer le code d'accès :", type="password")
        if st.button("Valider"):
            if pwd == CODE_SECRET:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Code d'accès incorrect.")
        return False
    return True

if check_password():
    
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.title("🚀 Navigation")
        st.info("Ceci est l'App 1 : Analyse Métier et Intégration SAP B1.")
        st.link_button("📊 Aller vers l'App 2 (Matrice 4.0 & Radar)", "https://votre-app-matrice.streamlit.app")
        st.divider()
        st.write("Moteur : **Groq (Llama 3.3 70B)**")

    # ==========================================
    # 🔑 CONFIGURATION GROQ
    # ==========================================
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    
    # Modèle le plus intelligent de Groq (équivalent GPT-4) pour des réponses longues et sans erreurs
    MODEL_NAME = "llama-3.3-70b-versatile"

    def parse_bpmn_from_file(file_object):
        """Extrait uniquement les tâches pour ne pas saturer le quota Groq."""
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
            lane_map = {node_ref.text: lane.get('name', 'Général') 
                        for lane in root.findall('.//bpmn:lane', ns) 
                        for node_ref in lane.findall('bpmn:flowNodeRef', ns)}
            
            tasks = []
            for elem in root.findall('.//bpmn:process/*', ns):
                if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                    e_name = elem.get('name', 'Sans nom').strip()
                    lane = lane_map.get(elem.get('id'), 'Général')
                    if e_name != 'Sans nom':
                        tasks.append(f"- [{lane}] {e_name}")

            return "\n".join(tasks)
        except Exception as e:
            return None

    def generate_analysis(tasks):
        """Génère l'analyse détaillée avec le bouclier anti-hallucination SAP."""
        prompt = f"""
        Tu es un Architecte Senior SAP Business One 10.0. 
        Voici la liste des tâches du processus :
        {tasks}

        🛑 RÈGLES STRICTES ANTI-HALLUCINATION (SAP B1 10.0 STANDARD UNIQUEMENT) :
        - Ne JAMAIS citer l'objet 'OINS' pour la qualité. Le module Qualité natif n'existe pas, propose d'utiliser des Champs Utilisateurs (UDF) sur les lignes de production ou des requêtes formatées.
        - Un processus de fabrication se fait dans UN SEUL Ordre de Fabrication (OWOR).
        - Les traitements intermédiaires (lavage, ozone, etc.) sont des Lignes de type 'Ressource' (ORSC) dans l'OF.
        - La validation se fait via 'Déclaration de production' (OIGN) ou 'Sortie pour production' (OIGE).
        - L'expédition vers l'export se fait via une 'Livraison' (ODLN), pas une commande.
        - Précise toujours les tables exactes (ex: OITM pour articles, OITW pour stocks, OJDT pour écritures comptables).

        Génère un rapport de très haute qualité avec EXACTEMENT ces 3 sections :

        ### 1. 📊 Tableau Synthétique
        (Colonnes : Département | Tâche)

        ### 2. 📝 Description Logique du Processus
        Rédige une analyse EXTRÊMEMENT détaillée et longue (au minimum 4 paragraphes riches) expliquant le flux métier de bout en bout. 

        ### 3. 🔵 Architecture SAP Business One 10.0
        Pour chaque tâche informatisable (ignore les tâches purement physiques comme couper ou laver), fournis une documentation technique détaillée sous forme de liste à puces :
        * **[Nom exact de la tâche]**
          * **Objet SAP & Chemin Menu :** [Ex: Menu Principal > Production > Déclaration de production (OIGN)]
          * **Données Maîtres (Master Data) :** [Les fiches OITM, OITT, ORSC, ou OCRD nécessaires]
          * **Action Utilisateur & Impact Système :** [Sois TRES BAVARD ici. Explique précisément les champs que l'utilisateur doit remplir et ce que le système fait en arrière-plan avec le stock et la valorisation comptable].
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es l'expert mondial sur SAP B1. Tu fournis des réponses extrêmement longues, détaillées, et sans aucune hallucination technique."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Température basse pour garantir la rigueur technique
            max_tokens=3500  # Limite sécurisée pour éviter l'erreur 413, tout en laissant la place pour un texte très long
        )
        return response.choices[0].message.content

    # ==========================================
    # 🏁 UI PRINCIPALE
    # ==========================================
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "bpmn_context" not in st.session_state: st.session_state.bpmn_context = ""

    st.title("🏭 App 1 : Hub d'Analyse Métier ➔ Architecture SAP B1")
    
    tab1, tab2 = st.tabs(["📊 Analyse & Suggestions", "💬 Assistant Configuration SAP"])

    # --- ONGLET 1 : ANALYSE ---
    with tab1:
        st.write("Importez votre processus pour générer l'architecture technique. (*Modèle : Groq Llama 3.3 70B*)")
        uploaded_file = st.file_uploader("Fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file:
            if st.button("🚀 Générer l'Analyse SAP Détaillée", type="primary"):
                with st.spinner("L'Architecte Senior rédige votre documentation technique..."):
                    tasks_txt = parse_bpmn_from_file(uploaded_file)
                    
                    if tasks_txt:
                        st.session_state.bpmn_context = tasks_txt
                        try:
                            report = generate_analysis(tasks_txt)
                            st.success("Analyse terminée ! Vous pouvez utiliser Ctrl+P pour l'imprimer proprement.")
                            st.markdown(report)
                        except Exception as e:
                            st.error(f"❌ Erreur Groq : {e} - Si c'est une erreur 429, attendez 60 secondes.")
                    else:
                        st.error("Impossible de lire le fichier BPMN.")

    # --- ONGLET 2 : CHAT ---
    with tab2:
        st.header("Discutez avec votre Architecte SAP")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input("Posez une question technique sur l'intégration SAP B1..."):
            if not st.session_state.bpmn_context:
                st.warning("Veuillez d'abord analyser un fichier dans l'onglet 'Analyse'.")
            else:
                with st.chat_message("user"): 
                    st.markdown(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})

                chat_prompt = f"""
                Tu es un consultant expert SAP B1 10.0.
                Contexte des tâches du processus : {st.session_state.bpmn_context}
                
                Question de l'utilisateur : {user_prompt}
                
                🛑 RÈGLE D'OR : Réponds de manière très détaillée. N'invente jamais de tables ou de modules qui n'existent pas dans le standard SAP B1 10.0 (Pas de module qualité natif OINS, tout se fait via OF, OIGN, ODLN ou UDF).
                """
                
                with st.chat_message("assistant"):
                    with st.spinner("Recherche des spécifications techniques SAP..."):
                        try:
                            response = client.chat.completions.create(
                                model=MODEL_NAME,
                                messages=[
                                    {"role": "system", "content": "Tu es un expert SAP B1 rigoureux et détaillé."},
                                    {"role": "user", "content": chat_prompt}
                                ],
                                temperature=0.1,
                                max_tokens=1500
                            )
                            ans = response.choices[0].message.content
                            st.markdown(ans)
                            st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        except Exception as e:
                            st.error(f"❌ Erreur Chat Groq : {e}")
