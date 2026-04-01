import streamlit as st
import xml.etree.ElementTree as ET
from groq import Groq
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page ---
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION PROPRE (CTRL+P)
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
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput {
        display: none !important;
    }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; font-size: 11px; }
    tr { page-break-inside: avoid; page-break-after: auto; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ (LOGIN)
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
        st.text_input("Veuillez entrer le code d'accès :", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Accès Restreint")
        st.text_input("Veuillez entrer le code d'accès :", type="password", on_change=password_entered, key="password")
        st.error("😕 Code d'accès incorrect.")
        return False
    else:
        return True

if check_password():
    
    # ==========================================
    # 🔑 INITIALISATION DE GROQ API
    # ==========================================
    # Assurez-vous d'avoir ajouté GROQ_API_KEY dans vos secrets Streamlit
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    
    # On utilise le modèle Llama 3 70B de Groq : extrêmement rapide et intelligent
    MODEL_NAME = "llama3-70b-8192"

    # --- LISTE DES PILIERS ---
    PILIERS = {
        1: "Big Data / Analytics",
        2: "Robots Autonomes",
        3: "Simulation",
        4: "Intégration Systèmes",
        5: "IIoT",
        6: "Cybersécurité",
        7: "Cloud Computing",
        8: "Fabrication Additive",
        9: "Réalité Augmentée"
    }

    def parse_bpmn_from_file(file_object):
        try:
            tree = ET.parse(file_object)
            root = tree.getroot()
        except Exception as e:
            return None, f"Erreur de lecture BPMN : {e}"

        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        lane_map = {}
        for lane in root.findall('.//bpmn:lane', ns):
            lane_name = lane.get('name', 'Général')
            for node_ref in lane.findall('bpmn:flowNodeRef', ns):
                lane_map[node_ref.text] = lane_name

        elements = {}
        tasks_list = []
        for elem in root.findall('.//bpmn:process/*', ns):
            if 'id' in elem.attrib and 'sequenceFlow' not in elem.tag:
                elem_id = elem.get('id')
                elem_name = elem.get('name', 'Sans nom').strip()
                elem_type = elem.tag.split('}')[-1] 
                lane_name = lane_map.get(elem_id, 'Général')
                elements[elem_id] = {'name': elem_name, 'type': elem_type, 'lane': lane_name}
                if elem_name != 'Sans nom':
                    tasks_list.append(f"- Étape: {lane_name} | Processus: {elem_name} | Type: {elem_type}")
                
        return "\n".join(tasks_list)

    # ==========================================
    # 🤖 FONCTIONS DE GÉNÉRATION GROQ SÉPARÉES
    # ==========================================

    def generate_part1_analysis(tasks_text):
        prompt = f"""
        Voici les données du processus métier :
        TÂCHES : {tasks_text}

        Génère une analyse EXTRÊMEMENT PRÉCISE, FACTUELLE et SANS AUCUNE HALLUCINATION.
        Structure ta réponse EXACTEMENT avec ces 3 parties :

        ### 1. 📊 Tableau Synthétique des Tâches
        Dresse un tableau Markdown concis récapitulant les tâches (Étape, Processus, Type de Tâche).

        ### 2. 📝 Description Logique du Processus
        Rédige une description chronologique, professionnelle et concise du flux.

        ### 3. 🔵 Propositions d'Intégration SAP Business One 10.0
        RÈGLES STRICTES ANTI-HALLUCINATION POUR CETTE SECTION :
        - Règle 1 : Limite-toi STRICTEMENT au standard de SAP Business One 10.0. Interdiction absolue d'inventer des menus.
        - Règle 2 : Ne propose une intégration SAP QUE pour les tâches administratives ou informatisées. Ignore les tâches 100% physiques.
        - Règle 3 : Si une tâche pertinente n'a pas d'écran standard exact, précise "Nécessite un UDF". Ne mens jamais sur le standard.

        Format exact à puces :
        * **[Nom exact de la tâche]**
          * **Module :** [Ex: Ventes]
          * **Écran cible :** [Ex: Commande client]
          * **Proposition :** [Explication technique très précise]
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un Consultant Expert SAP Business One 10.0 et un Analyste BPMN Senior."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content

    def generate_single_pillar(tasks_text, pillar_name):
        prompt = f"""
        Génère un tableau d'évaluation UNIQUEMENT pour le pilier : {pillar_name}.
        
        RÈGLE ABSOLUE : Tu dois lister et évaluer TOUTES les tâches ci-dessous, sans exception.
        TÂCHES :
        {tasks_text}

        Colonnes du tableau Markdown : `Tâche BPMN` | `Score {pillar_name} (1-5)` | `Justification`.
        ASTUCE: Justification très courte (3 mots max).
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un Expert Industrie 4.0."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

    def generate_part3_radar(tasks_text):
        prompt = f"""
        Sur la base de ces tâches : {tasks_text}
        Calcule la note globale moyenne (1 à 5) du processus pour les 9 piliers de l'industrie 4.0.
        Génère UNIQUEMENT un bloc JSON valide, rien d'autre.
        ```json
        {{ "Big Data": 2, "Robots Autonomes": 1, "Simulation": 1, "Intégration Systèmes": 3, "IIoT": 2, "Cybersécurité": 4, "Cloud": 3, "Fabrication Additive": 1, "Réalité Augmentée": 1 }}
        ```
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un calculateur strict qui ne renvoie que du JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content

    def draw_radar_chart(json_str):
        try:
            scores = json.loads(json_str)
            df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], 
                                title="Indice de Maturité I4.0 (9 Piliers)", markers=True)
            fig.update_traces(fill='toself', line_color='#ff7f0e') 
            return fig
        except: return None

    # ==========================================
    # 💾 INITIALISATION DE LA MÉMOIRE (SESSION)
    # ==========================================
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "bpmn_tasks_only" not in st.session_state: st.session_state.bpmn_tasks_only = ""
    
    if "step1_text" not in st.session_state: st.session_state.step1_text = ""
    if "step3_text" not in st.session_state: st.session_state.step3_text = ""
    
    if "pillar_scores" not in st.session_state: 
        st.session_state.pillar_scores = {i: "" for i in range(1, 10)}

    st.title("💡 Hub d'Intégration : BPMN ➔ SAP Business One 10.0")

    tab1, tab2 = st.tabs(["📊 Évaluation à la Carte", "💬 Assistant SAP"])

    with tab1:
        st.write("Importez votre processus. 🖨️ *Astuce : Faites Ctrl+P pour imprimer un rapport propre.*")
        uploaded_file = st.file_uploader("Importez votre fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            # Extraction
            if not st.session_state.bpmn_tasks_only:
                tasks_text = parse_bpmn_from_file(uploaded_file)
                if tasks_text is None: st.error("Erreur de lecture du fichier.")
                else: st.session_state.bpmn_tasks_only = tasks_text

            # BOUTON 1 : RESET
            if st.button("🔄 Réinitialiser complètement", type="secondary"):
                st.session_state.step1_text = ""
                st.session_state.step3_text = ""
                st.session_state.pillar_scores = {i: "" for i in range(1, 10)}
                st.rerun()

            st.divider()
            
            # =========================================================
            # SECTION 1 : SAP & MÉTIER 
            # =========================================================
            st.subheader("Étape 1 : Analyse Métier & Architecture SAP B1")
            if not st.session_state.step1_text:
                if st.button("📝 Générer l'Analyse Métier et SAP", type="primary"):
                    with st.spinner("Analyse approfondie du standard SAP en cours..."):
                        try:
                            st.session_state.step1_text = generate_part1_analysis(st.session_state.bpmn_tasks_only)
                            st.rerun()
                        except Exception as e: st.error(f"Erreur : {e}")
            else:
                st.success("✅ Analyse SAP générée avec succès.")
                st.markdown(st.session_state.step1_text)

            st.divider()

            # =========================================================
            # SECTION 2 : LES 9 PILIERS I4.0 
            # =========================================================
            st.subheader("Étape 2 : Évaluation des 9 Piliers (Industrie 4.0)")
            st.write("Générez les tableaux un par un. (Avec Groq, c'est presque instantané ⚡)")
            
            # Grille de 3 colonnes pour les 9 boutons
            cols = st.columns(3)
            for i, (num, name) in enumerate(PILIERS.items()):
                col = cols[i % 3]
                with col:
                    if not st.session_state.pillar_scores[num]:
                        if st.button(f"⚙️ Générer : {name}", key=f"btn_{num}", use_container_width=True):
                            with st.spinner(f"Génération rapide pour {name}..."):
                                try:
                                    st.session_state.pillar_scores[num] = generate_single_pillar(st.session_state.bpmn_tasks_only, name)
                                    st.rerun()
                                except Exception as e: st.error(f"Erreur : {e}")
                    else:
                        st.success(f"✅ {name} généré")

            # Affichage direct et visible des tableaux générés
            for num, name in PILIERS.items():
                if st.session_state.pillar_scores[num]:
                    st.markdown(f"### 📊 Score : {name}")
                    st.markdown(st.session_state.pillar_scores[num])
                    st.write("---")

            st.divider()

            # =========================================================
            # SECTION 3 : RÉSULTATS & RADAR 
            # =========================================================
            st.subheader("Étape 3 : Synthèse & Graphique Radar")
            if not st.session_state.step3_text:
                if st.button("📈 Générer le Radar Final", type="primary"):
                    with st.spinner("Calcul des notes finales..."):
                        try:
                            st.session_state.step3_text = generate_part3_radar(st.session_state.bpmn_tasks_only)
                            st.rerun()
                        except Exception as e: st.error(f"Erreur : {e}")
            else:
                st.success("✅ Graphique Radar généré.")
                report_part3 = st.session_state.step3_text
                json_match = re.search(r'```json\n(.*?)\n```', report_part3, re.DOTALL)
                
                if json_match:
                    json_data = json_match.group(1)
                    col_vide1, col_centre, col_vide2 = st.columns([1, 2, 1])
                    with col_centre:
                        try:
                            scores_dict = json.loads(json_data)
                            df_scores = pd.DataFrame(list(scores_dict.items()), columns=['Pilier 4.0', 'Note globale'])
                            st.dataframe(df_scores, hide_index=True, use_container_width=True)
                        except Exception as e: pass

                        fig = draw_radar_chart(json_data)
                        if fig: st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Erreur de format du radar.")

    # ==========================================
    # 💬 ONGLET 2 : LE CHAT EXPERT SÉCURISÉ
    # ==========================================
    with tab2:
        st.header("Discutez avec votre Consultant SAP B1")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_prompt := st.chat_input("Posez votre question sur SAP B1..."):
            if not st.session_state.bpmn_tasks_only:
                st.warning("Veuillez d'abord importer un fichier dans le premier onglet.")
            else:
                with st.chat_message("user"): st.markdown(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})

                chat_context = f"""
                Tu es un consultant expert SAP Business One 10.0. L'utilisateur te pose une question sur son processus métier.
                RÈGLE 1 : Réponses applicables STRICTEMENT ET UNIQUEMENT à SAP Business One 10.0. Ne mentionne pas S/4HANA ou ECC.
                RÈGLE 2 : Si tu n'es pas certain, dis 'Cette fonction n'existe pas en standard'. N'invente jamais de chemins.
                Voici les données du processus actuel : {st.session_state.bpmn_tasks_only}
                Question : {user_prompt}
                """
                with st.chat_message("assistant"):
                    with st.spinner("Réflexion..."):
                        try:
                            response = client.chat.completions.create(
                                model=MODEL_NAME,
                                messages=[
                                    {"role": "system", "content": "Tu es un consultant SAP B1 10.0 hyper rigoureux."},
                                    {"role": "user", "content": chat_context}
                                ],
                                temperature=0.0
                            )
                            ans = response.choices[0].message.content
                            st.markdown(ans)
                            st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        except Exception as e:
                            st.error(f"🔴 Erreur API Groq : {e}")
