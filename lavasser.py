import streamlit as st
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types 
import plotly.express as px
import pandas as pd
import json
import re

# --- Configuration de la page ---
st.set_page_config(page_title="Assistant BPMN & SAP B1", page_icon="🏭", layout="wide")

# ==========================================
# 🖨️ CSS POUR IMPRESSION PROPRE
# ==========================================
st.markdown("""
<style>
@media print {
    body, html, .stApp, .main, section, div.block-container { height: auto !important; overflow: visible !important; display: block !important; position: relative !important; }
    header, footer, [data-testid="stSidebar"], .stButton, .stFileUploader, .stTextInput { display: none !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    table { page-break-inside: auto; width: 100% !important; font-size: 11px; }
    tr { page-break-inside: avoid; page-break-after: auto; }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SYSTÈME DE SÉCURITÉ
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
    
    # ==========================================
    # 🔑 INITIALISATION DU MOTEUR HAUTE PRÉCISION
    # ==========================================
    API_KEY = st.secrets["API_KEY"] 
    client = genai.Client(api_key=API_KEY)
    
    # On utilise le modèle PRO pour une expertise SAP B1 maximale et aucune limite de texte
    MODEL_NAME = 'gemini-1.5-pro'

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
                    tasks_list.append(f"- [{lane_name}] {elem_name}")
        
        flows = []
        for flow in root.findall('.//bpmn:sequenceFlow', ns):
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            condition = flow.get('name', '') 
            if source in elements and target in elements:
                s_elem = elements[source]
                t_elem = elements[target]
                flow_desc = f"De '{s_elem['name']}' -> Vers '{t_elem['name']}'"
                if condition: flow_desc += f" [Condition: {condition}]"
                flows.append(flow_desc)
                
        return "\n".join(tasks_list), "\n".join(flows)

    # ==========================================
    # 🤖 FONCTIONS DE GÉNÉRATION DÉTAILLÉES
    # ==========================================

    def generate_part1_analysis(tasks_text, flows_text):
        prompt = f"""
        Voici le processus métier d'une entreprise industrielle :
        TÂCHES : {tasks_text}
        FLUX : {flows_text}

        Ta mission est de rédiger la "Première Partie" du rapport. C'est la plus importante. Elle doit être EXTRÊMEMENT DÉTAILLÉE, LONGUE et TECHNIQUE. Zéro hallucination.

        ### 1. 📊 Synthèse des Tâches
        Dresse un tableau Markdown classique (Département | Tâche).

        ### 2. 📝 Description Logique et Métier
        Analyse profonde en 3 ou 4 paragraphes. Décris le flux de bout en bout, les dépendances et la valeur ajoutée du processus. Ne sois pas bref.

        ### 3. 🔵 Architecture et Implémentation SAP Business One 10.0 (DÉTAILS MAXIMAUX)
        Pour chaque tâche informatisable, je veux une véritable documentation d'implémentation. Ignore totalement les tâches purement manuelles (laver, couper, coudre).
        Format OBLIGATOIRE pour chaque tâche :
        * **[Nom exact de la tâche]**
          * **Module SAP & Chemin :** [Ex: Modules > Production > Ordre de fabrication]
          * **Données de Base (Master Data) :** [Quelles fiches doivent exister ? Ex: Fiche Article (OITM), Nomenclature (OITT)]
          * **Écran Transactionnel cible :** [Quel document SAP créer ?]
          * **Détail de l'opération & Impact Système :** [Paragraphe TRES détaillé expliquant comment l'utilisateur remplit l'écran, et ce que fait SAP en arrière-plan (ex: Mouvement de stock, Écriture au journal, Statut de l'OF).]
          * **Personnalisation :** [Si le standard ne suffit pas, propose un UDF (Champ Utilisateur) précis.]
        """
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Tu es le meilleur Architecte Solution SAP Business One 10.0 au monde.",
                temperature=0.2,
                max_output_tokens=8192
            )
        )
        return response.text

    def generate_part2_evaluation(tasks_text):
        prompt = f"""
        Génère UN SEUL grand tableau Markdown d'évaluation Industrie 4.0 pour TOUTES les tâches suivantes :
        
        {tasks_text}

        RÈGLES IMPÉRATIVES :
        1. Tu DOIS lister et évaluer ABSOLUMENT TOUTES les tâches fournies (il y en a beaucoup).
        2. Le tableau DOIT comporter EXACTEMENT 11 colonnes.
        
        Format strict du tableau :
        | Tâche BPMN | Big Data | Robots | Simul. | Intégr. | IIoT | Cyber. | Cloud | Additif | RA | Justification Détaillée |
        |---|---|---|---|---|---|---|---|---|---|---|
        | [Nom de la tâche] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [Une phrase expliquant pourquoi ces notes ont été attribuées] |

        Renvoie UNIQUEMENT le code Markdown du tableau. Aucun blabla avant ou après.
        """
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Tu es un Expert Industrie 4.0 rigoureux. Tu génères un tableau Markdown géant et complet.",
                temperature=0.1,
                max_output_tokens=8192
            )
        )
        return response.text

    def generate_part3_radar(tasks_text):
        prompt = f"""
        Calcule la moyenne globale des scores pour les 9 piliers de l'Industrie 4.0 en te basant sur le processus fourni.
        
        RÈGLE ABSOLUE : Tu dois renvoyer UNIQUEMENT un objet JSON. 
        Les CLÉS du JSON doivent être EXACTEMENT les 9 piliers ci-dessous. NE METS SURTOUT PAS LES NOMS DES TÂCHES COMME CLÉS.
        
        Exemple STRICT du format attendu :
        {{
          "Big Data & Analytics": 3.2,
          "Robots Autonomes": 1.5,
          "Simulation": 2.0,
          "Intégration Systèmes": 4.1,
          "IIoT": 2.5,
          "Cybersécurité": 3.0,
          "Cloud Computing": 4.0,
          "Fabrication Additive": 1.0,
          "Réalité Augmentée": 1.0
        }}
        """
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Tu es un script Python qui ne renvoie STRICTEMENT que du JSON valide.",
                temperature=0.0,
            )
        )
        return response.text

    def draw_radar_chart(json_str):
        try:
            # Extraction ultra-robuste pour éviter le bug de la page 6 de votre PDF
            json_match = re.search(r'\{[\s\S]*\}', json_str)
            if not json_match:
                return None
            scores = json.loads(json_match.group(0))
            
            # Vérification de sécurité : si l'IA a mis des tâches au lieu des 9 piliers, on bloque
            if len(scores.keys()) > 12:
                return None
                
            df = pd.DataFrame(dict(r=list(scores.values()), theta=list(scores.keys())))
            fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0,5], 
                                title="Indice de Maturité I4.0 Global", markers=True)
            fig.update_traces(fill='toself', line_color='#ff7f0e') 
            return fig
        except Exception as e: 
            return None

    # ==========================================
    # 💾 SESSION STATE
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
        st.write("Importez votre processus. Propulsé par **Gemini 1.5 Pro** (Expertise SAP Maximale).")
        uploaded_file = st.file_uploader("Fichier .bpmn ou .xml", type=['bpmn', 'xml'])

        if uploaded_file is not None:
            if not st.session_state.bpmn_tasks_only:
                tasks_text, flows_text = parse_bpmn_from_file(uploaded_file)
                if tasks_text is None: st.error("Erreur de lecture.")
                else: 
                    st.session_state.bpmn_tasks_only = tasks_text
                    st.session_state.bpmn_flows_only = flows_text

            if st.button("🔄 Réinitialiser l'analyse", type="secondary"):
                st.session_state.step1_text = ""
                st.session_state.step2_text = ""
                st.session_state.step3_text = ""
                st.rerun()

            st.divider()
            
            # --- BOUTONS ---
            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if not st.session_state.step1_text:
                    if st.button("1️⃣ Analyse Métier & SAP Détaillée", use_container_width=True, type="primary"):
                        with st.spinner("Rédaction du rapport SAP détaillé par l'Architecte Expert..."):
                            try:
                                st.session_state.step1_text = generate_part1_analysis(st.session_state.bpmn_tasks_only, st.session_state.bpmn_flows_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur : {e}")
                else: st.success("✅ Étape 1 : Terminée")

            with col_b2:
                if not st.session_state.step2_text:
                    if st.button("2️⃣ Matrice d'Évaluation 4.0", use_container_width=True, type="primary"):
                        with st.spinner("Génération de l'unique grand tableau (Patientez, traitement de 80 tâches)..."):
                            try:
                                st.session_state.step2_text = generate_part2_evaluation(st.session_state.bpmn_tasks_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur API : {e}")
                else: st.success("✅ Étape 2 : Terminée")

            with col_b3:
                if not st.session_state.step3_text:
                    if st.button("3️⃣ Graphique Radar Final", use_container_width=True, type="primary"):
                        with st.spinner("Calcul des notes et du JSON..."):
                            try:
                                st.session_state.step3_text = generate_part3_radar(st.session_state.bpmn_tasks_only)
                                st.rerun()
                            except Exception as e: st.error(f"Erreur : {e}")
                else: st.success("✅ Étape 3 : Terminée")

            st.divider()

            # --- RÉSULTATS ---
            if st.session_state.step1_text:
                st.markdown(st.session_state.step1_text)
                st.divider()

            if st.session_state.step2_text:
                st.markdown("### 🏭 Matrice d'Évaluation Complète (Industrie 4.0)")
                st.markdown(st.session_state.step2_text)
                st.divider()

            if st.session_state.step3_text:
                st.subheader("📊 Résultats Globaux")
                report_part3 = st.session_state.step3_text
                
                json_match = re.search(r'\{[\s\S]*\}', report_part3)
                if json_match:
                    json_data = json_match.group(0)
                    col_vide1, col_centre, col_vide2 = st.columns([1, 2, 1])
                    with col_centre:
                        try:
                            scores_dict = json.loads(json_data)
                            if len(scores_dict.keys()) > 10:
                                st.error("L'IA a encore listé les tâches au lieu des piliers. Veuillez cliquer sur 'Réinitialiser' et recommencer l'étape 3.")
                            else:
                                df_scores = pd.DataFrame(list(scores_dict.items()), columns=['Pilier 4.0', 'Note moyenne'])
                                st.dataframe(df_scores, hide_index=True, use_container_width=True)
                        except Exception as e: 
                            pass

                        fig = draw_radar_chart(json_data)
                        if fig: st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Erreur : Impossible d'extraire les données du Radar.")
                    st.code(report_part3)

    # ==========================================
    # 💬 ONGLET 2 : CHAT SAP
    # ==========================================
    with tab2:
        st.header("Discutez avec votre Consultant SAP B1")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_prompt := st.chat_input("Posez votre question SAP B1..."):
            if not st.session_state.bpmn_tasks_only:
                st.warning("Importez d'abord un fichier.")
            else:
                with st.chat_message("user"): st.markdown(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})

                chat_context = f"""
                Tu es un consultant expert SAP Business One 10.0. 
                RÈGLE 1 : Uniquement B1 10.0 standard (pas ECC, pas S/4HANA).
                RÈGLE 2 : Dis 'Je ne sais pas' si la fonction n'existe pas. Zéro hallucination.
                Processus : {st.session_state.bpmn_tasks_only}
                Question : {user_prompt}
                """
                with st.chat_message("assistant"):
                    with st.spinner("Recherche dans la documentation SAP..."):
                        try:
                            response = client.models.generate_content(
                                model=MODEL_NAME,
                                contents=chat_context,
                                config=types.GenerateContentConfig(
                                    system_instruction="Tu es rigoureux, tu ne mens jamais sur les capacités de SAP B1.",
                                    temperature=0.0
                                )
                            )
                            ans = response.text
                            st.markdown(ans)
                            st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        except Exception as e:
                            st.error(f"🔴 Erreur API : {e}")
