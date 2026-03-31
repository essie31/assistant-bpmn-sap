import streamlit as st
from google import genai

st.set_page_config(page_title="Détective Google", layout="wide")
st.title("🕵️‍♂️ Détective de Modèles Google V2")

try:
    API_KEY = st.secrets["API_KEY"]
    client = genai.Client(api_key=API_KEY)
    
    st.write("🔍 **Recherche des modèles disponibles...**")
    
    # On récupère la liste brute
    modeles_disponibles = list(client.models.list())
    
    st.success(f"✅ Succès ! Voici les modèles liés à votre clé :")
    
    for m in modeles_disponibles:
        # On affiche simplement le nom exact du modèle
        st.markdown(f"- 🟢 **`{m.name}`**")
            
except Exception as e:
    st.error(f"Erreur : {e}")
