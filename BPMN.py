import streamlit as st
from google import genai

st.set_page_config(page_title="Détective Google", layout="wide")
st.title("🕵️‍♂️ Détective de Modèles Google")

# Récupération de la clé depuis les secrets de Streamlit
try:
    API_KEY = st.secrets["API_KEY"]
    client = genai.Client(api_key=API_KEY)
    
    st.write("🔍 **Recherche des modèles disponibles pour votre clé API...**")
    
    # On demande à Google sa liste officielle
    modeles_disponibles = list(client.models.list())
    
    st.success(f"✅ Google a répondu ! Voici les {len(modeles_disponibles)} modèles que vous pouvez utiliser :")
    
    for m in modeles_disponibles:
        # On ne garde que ceux qui peuvent générer du texte
        if 'generateContent' in m.supported_generation_methods:
            st.markdown(f"- 🟢 Nom exact à copier : **`{m.name}`**")
            
except Exception as e:
    st.error(f"Impossible de récupérer la liste. Erreur : {e}")
