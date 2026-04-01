import streamlit as st
import xml.etree.ElementTree as ET
from groq import Groq
import plotly.express as px
import pandas as pd
import json
import re
import time

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
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)
    
    MODEL_NAME = "llama-3.1-8b-instant"

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
        
        flows = []
        for flow in root.findall('.//bpmn:sequenceFlow', ns):
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            condition = flow.get('name', '') 
            if source in elements and target in elements:
                s_elem = elements[source]
                t_elem = elements[target]
                flow_desc = f"De [{s_elem['lane']}] '{s_elem['name']}' -> Vers [{t_elem['lane']}] '{t_elem['name']}'"
                if condition: flow_desc += f" [Condition: {condition}]"
                flows.append(flow_desc)
                
        return "\n".join(tasks_list), "\n".join(flows)

    # ==========================================
    # 🤖 FONCTIONS DE GÉNÉRATION GROQ
    # ==========================================

    def generate_part1_analysis(tasks_text, flows_text):
        prompt = f"""
        Voici les données du processus métier complet :
        TÂCHES : {tasks_text}
        FLUX ET LOGIQUE : {flows_text}

        Génère une analyse EXTRÊMEMENT DÉTAILLÉE, PRÉCISE et SANS AUCUNE HALLUCINATION.
        Structure ta réponse EXACTEMENT avec ces 3 parties :

        ### 1. 📊 Tableau Synthétique des Tâches
        Dresse un tableau Markdown exhaustif récapitulant les tâches.

        ### 2. 📝 Description Logique du Processus
        Rédige une description chronologique approfondie du flux, en expliquant les dépendances entre les étapes.

        ### 3. 🔵 Propositions d'Intégration SAP Business One 10.0 (ULTRA DÉTAILLÉES)
        RÈGLES STRICTES :
        - Limite-toi STRICTEMENT au standard SAP B1 10.0. Interdiction absolue d'inventer des menus.
        - Ignore les tâches 100% physiques.
        - Si pas de standard, précise "Nécessite un Champ Utilisateur (UDF)".

        Pour CHAQUE tâche pertinente, sois très généreux en détails techniques. Format requis :
        * **[Nom exact de la tâche]**
          * **Module :** [Ex: Ventes]
          * **Écran cible :** [Ex: Commande client]
          * **Chemin de navigation :** [Ex: Menu principal > Ventes - Client > Commande client]
          * **Détails de l'action SAP :** [Explique de manière approfondie quels champs remplir, quelles sont les données de base pré-requises, et quel sera l'impact système.]
        """
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Tu es un Consultant Expert Senior SAP Business One 10.0 et un Analyste BPMN."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content

    # LA MAGIE EST ICI : Le code va forcer l'IA à générer les 9 tableaux un par un, puis les coller.
    def generate_part2_evaluation(tasks_text):
        full_markdown = ""
        my_bar = st.progress(0, text="Démarrage de la génération des 9 tableaux...")
        
        for i, (num, pillar_name) in enumerate(PILIERS.items()):
            my_bar.progress((i) / 9, text=f"🤖 Génération du tableau : {pillar_name} ({i+1}/9)...")
            
            prompt = f"""
            Génère un tableau d'évaluation UNIQUEMENT pour le pilier : {pillar_name}.
            
            RÈGLE ABSOLUE : Tu dois lister et évaluer TOUTES les tâches ci-dessous, sans exception.
            TÂCHES :
            {tasks_text}

            Colonnes du tableau Markdown : `Tâche BPMN` | `Score {pillar_name} (1-5)` | `Justification`.
            Ne génère AUCUN texte avant ou après le tableau. Uniquement le code du tableau Markdown.
            """
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Tu es un Expert Industrie 4.0 strict. Tu ne renvoies que des tableaux Markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            full_markdown += f"### 📊 Score : {pillar_name}\n\n"
            full_markdown += response.choices[0].message.content + "\n\n---\n\n"
            
        my_bar.progress(1.0, text="✅ Les 9 tableaux sont générés !")
        time.sleep(1) # Laisse le temps à l'utilisateur de lire le message de succès
        my_bar.empty() # Efface la barre de progression
        
        return full_markdown

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
    if "bpmn_flows_only" not in st.session_state: st.session_state.bpmn_flows_only = ""
    
    if "step1_text" not in st.session_state: st.session_state.step1_text = ""
    if "step2_text" not in st.session_state: st.session_state.step2_text = ""
    if "step3_text" not in st.session_state: st.session_state.step3_text = ""

    st.title("💡 Hub d'Intégration : BPMN ➔ SAP Business One 10.0")

    tab1, tab2 = st.tabs(["📊 Évaluation en 3 Étapes", "💬 Assistant SAP"])

    with tab1:
        st.write("Importez votre processus. Génération robuste via Groq Llama 3 ⚡.")
        uploaded_file = st.file_uploader("Importez votre fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            # Extraction
            if not st.session_state.bpmn_tasks_only:
                tasks_text, flows_text = parse_bpmn_from_file(uploaded_file)
                if tasks_text is None: st.error("Erreur de lecture du fichier.")
                else: 
                    st.session_state.bpmn_tasks_only = tasks_text
                    st.session_state.bpmn_flows_only = flows_text

            # BOUTON DE RÉINITIALISATION
            if st.button("🔄 Réinitialiser complètement", type="secondary"):
                st.session_state.step1_text = ""
                st.session_state.step2_text = ""
                st.session_state.step3_text = ""
                st.rerun()

            st.divider()
            
            # =========================================================
            # LES 3 BOUTONS PRINCIPAUX
            # =========================================================
            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if not st.session_state.step1_text:
                    if st.button("1️⃣ Analyse Métier & SAP Détaillée", use_container_width=True, type="primary"):
                        with st.spinner("Analyse approfondie en cours..."):
                            try:
                                st.session_state.step1_text = generate_part1_analysis(st.session_state.bpmn_tasks_only, st.session_state.bpmn_flows_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur : {e}")
                else:
                    st.success("✅ Étape 1 : Terminée")

            with col_b2:
                if not st.session_state.step2_text:
                    if st.button("2️⃣ Les 9 Tableaux de Scoring", use_container_width=True, type="primary"):
                        # Le chargement est géré par la barre de progression dans la fonction
                        try:
                            st.session_state.step2_text = generate_part2_evaluation(st.session_state.bpmn_tasks_only)
                            st.rerun()
                        except Exception as e: st.error(f"Erreur : {e}")
                else:
                    st.success("✅ Étape 2 : Terminée")

            with col_b3:
                if not st.session_state.step3_text:
                    if st.button("3️⃣ Graphique Radar Final", use_container_width=True, type="primary"):
                        with st.spinner("Calcul des scores..."):
                            try:
                                st.session_state.step3_text = generate_part3_radar(st.session_state.bpmn_tasks_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur : {e}")
                else:
                    st.success("✅ Étape 3 : Terminée")

            st.divider()

            # =========================================================
            # AFFICHAGE DES RÉSULTATS DANS L'ORDRE
            # =========================================================
            if st.session_state.step1_text:
                st.markdown(st.session_state.step1_text)
                st.divider()

            if st.session_state.step2_text:
                st.markdown("### 🏭 Évaluation des Tâches selon les 9 Piliers (Industrie 4.0)")
                st.markdown(st.session_state.step2_text)
                st.divider()

            if st.session_state.step3_text:
                st.subheader("📊 Scores Globaux (9 Piliers)")
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
