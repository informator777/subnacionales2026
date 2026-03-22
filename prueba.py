import streamlit as st

st.title("📊 Sistema de Votos - Alianza Patria Sol")
st.write("Bienvenido, Marcelo. El entorno Python 3.11 está listo.")

nombre = st.text_input("Ingresa un municipio para filtrar:")
if nombre:
    st.success(f"Buscando datos para: {nombre}")