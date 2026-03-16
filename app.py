"""
Este módulo contiene la lógica principal para mi aplicación de Streamlit.
"""

import os
from datetime import datetime
import streamlit as st
import pandas as pd



# Configuración de la página
st.set_page_config(page_title="Escrutinio Alianza Patria Sol", layout="wide")

# --- CARGA DE CATÁLOGOS ---
@st.cache_data
def cargar_datos():
    # Cargar Recintos
    recintos = ["Recinto General"]
    if os.path.exists("recintos.csv"):
        df_r = pd.read_csv("recintos.csv")
        recintos = df_r["Recinto"].unique().tolist()
    
    # Cargar Partidos
    partidos_df = pd.DataFrame(columns=["Sigla", "Nombre Candidato", "URL logo"])
    if os.path.exists("partidos.csv"):
        partidos_df = pd.read_csv("partidos.csv")
    else:
        st.error("⚠️ No se encontró partidos.csv")
        
    return recintos, partidos_df

lista_recintos, df_partidos = cargar_datos()
CATEGORIAS = ["Gobernador", "Asambleísta Departamental", "Asambleísta Regional", "Alcalde", "Concejal"]
DB_FILE = "votos_final.csv"

# --- INICIALIZACIÓN DE DB ---
if not os.path.exists(DB_FILE):
    columnas = ["Timestamp", "Circ", "Recinto", "Mesa", "Inscritos"]
    for cat in CATEGORIAS:
        for _, row in df_partidos.iterrows():
            columnas.append(f"{cat}_{row['Sigla']}")
        columnas += [f"{cat}_Blancos", f"{cat}_Nulos", f"{cat}_Obs"]
    pd.DataFrame(columns=columnas).to_csv(DB_FILE, index=False)

# --- INTERFAZ ---
st.title("🗳️ Sistema de Captura Electoral Pro")

with st.form("form_electoral"):
    # Fila de ubicación y Padrón
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1:
        circ = st.selectbox("Circunscripción", ["C-1", "C-2", "C-3"])
    with c2:
        recinto = st.selectbox("Recinto", lista_recintos)
    with c3:
        mesa = st.number_input("Nro Mesa", min_value=1, step=1)
    with c4:
        inscritos = st.number_input("Inscritos (Opcional)", min_value=0, step=1, help="Total habilitados en mesa")

    st.divider()

    datos_votos = {}

    # Generar entradas por Categoría
    for cat in CATEGORIAS:
        st.subheader(f"📍 {cat}")
        
        # Grid para candidatos + Blancos/Nulos
        # Calculamos columnas: Partidos + 2 (Blancos/Nulos)
        num_cols = len(df_partidos) + 2
        cols = st.columns(num_cols)
        
        # Iterar sobre partidos del CSV
        for i, (_, row) in enumerate(df_partidos.iterrows()):
            with cols[i]:
                # Mostrar Logo (simulado a 1cm aprox con width=40) y Sigla
                if os.path.exists(row['URL logo']):
                    st.image(row['URL logo'], width=40)
                else:
                    st.caption(f"[{row['Sigla']}]")
                
                st.write(f"**{row['Sigla']}**")
                st.caption(row['Nombre Candidato'])
                
                key = f"{cat}_{row['Sigla']}"
                datos_votos[key] = st.number_input("Votos", min_value=0, step=1, key=key, label_visibility="collapsed")

        # Blancos y Nulos al final de la fila de la categoría
        with cols[-2]:
            st.write("⚪ **Blancos**")
            key_b = f"{cat}_Blancos"
            datos_votos[key_b] = st.number_input("B", min_value=0, step=1, key=key_b, label_visibility="collapsed")
        
        with cols[-1]:
            st.write("❌ **Nulos**")
            key_n = f"{cat}_Nulos"
            datos_votos[key_n] = st.number_input("N", min_value=0, step=1, key=key_n, label_visibility="collapsed")

        # Observación por categoría
        key_obs = f"{cat}_Obs"
        datos_votos[key_obs] = st.text_input(f"Nota {cat}", key=key_obs, placeholder="Observaciones de categoría...")
        st.divider()

    btn_guardar = st.form_submit_button("💾 REGISTRAR ACTA")

# --- LÓGICA DE GUARDADO Y QA ---
if btn_guardar:
    # Validación básica de QA (Opcional)
    error_padrón = False
    if inscritos > 0:
        for cat in CATEGORIAS:
            suma_cat = sum([datos_votos[f"{cat}_{r['Sigla']}"] for _, r in df_partidos.iterrows()]) + \
                       datos_votos[f"{cat}_Blancos"] + datos_votos[f"{cat}_Nulos"]
            if suma_cat > inscritos:
                st.warning(f"⚠️ Alerta en {cat}: Suma de votos ({suma_cat}) supera inscritos ({inscritos})")
                error_padrón = True

    nuevo_reg = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Circ": circ, "Recinto": recinto, "Mesa": mesa, "Inscritos": inscritos,
        **datos_votos
    }
    
    pd.DataFrame([nuevo_reg]).to_csv(DB_FILE, mode='a', header=False, index=False)
    st.success(f"✅ Acta Mesa {mesa} registrada.")