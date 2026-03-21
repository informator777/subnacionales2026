import streamlit as st
import pandas as pd
import os
from datetime import datetime
import streamlit_authenticator as stauth
import altair as alt # <-- Importación necesaria para personalizar colores

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Escrutinio Alianza Patria Sol-C6", layout="wide", page_icon="🗳️")

# --- 2. DEFINICIÓN DE FUNCIONES (NIVEL PRINCIPAL) ---

@st.cache_data
def cargar_datos_maestros():
    df_m = pd.read_csv("recintos.csv") if os.path.exists("recintos.csv") else pd.DataFrame(columns=["circunscripcion","NombreDeRecinto","mesa","NroHabilitados"])
    df_p = pd.read_csv("partidos.csv") if os.path.exists("partidos.csv") else pd.DataFrame(columns=["Sigla", "Nombre Candidato", "logo"])
    return df_m, df_p

def esta_bloqueado_optimizado(df, rec, mes, cat):
    if df.empty or 'Categoría' not in df.columns: 
        return False
    filtro = df[(df['Recinto'] == rec) & 
                (df['Mesa'].astype(str) == str(mes)) & 
                (df['Categoría'] == cat)]
    return not filtro.empty

def generar_reporte_votos(df):
    st.subheader("📊 Resumen Ejecutivo de Votación")
    metadatos = ["Timestamp", "Usuario", "Circunscripcion", "Recinto", "Mesa", "Categoría", "Inscritos", "Votos_Validos", "Foto", "Obs"]
    columnas_partidos = [c for c in df.columns if c not in metadatos]
    
    if df.empty or 'Categoría' not in df.columns:
        st.info("No hay datos para reportar.")
        return

    # --- 1. SECCIÓN DE FILTROS ---
    f1, f2, f3 = st.columns(3)
    
    with f1:
        cat_reporte = st.selectbox("Categoría", df['Categoría'].unique(), key="sel_reporte_cat")
    
    # Aplicamos el primer filtro (Categoría) para alimentar las siguientes listas
    df_filtrado = df[df['Categoría'] == cat_reporte]
    
    with f2:
        lista_recintos = ["TODOS"] + sorted(df_filtrado['Recinto'].dropna().unique().tolist())
        rec_reporte = st.selectbox("Recinto", lista_recintos, key="sel_reporte_rec")
        
    # Aplicamos el segundo filtro (Recinto)
    if rec_reporte != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['Recinto'] == rec_reporte]
        
    with f3:
        # Convertimos las mesas a texto para evitar conflictos de formato y poder mezclar con "TODOS"
        lista_mesas = ["TODOS"] + sorted(df_filtrado['Mesa'].astype(str).dropna().unique().tolist())
        mesa_reporte = st.selectbox("Mesa", lista_mesas, key="sel_reporte_mes")
        
    # Aplicamos el tercer filtro (Mesa)
    if mesa_reporte != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['Mesa'].astype(str) == mesa_reporte]

    st.divider()

    # --- 2. RENDERIZADO DE RESULTADOS ---
    if not df_filtrado.empty:
        # Solo sumamos las columnas numéricas de los partidos
        totales = df_filtrado[columnas_partidos].apply(pd.to_numeric, errors='coerce').sum().sort_values(ascending=False)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Mesas Computadas en este filtro", len(df_filtrado))
        
        if not totales.empty and totales.iloc[0] > 0:
            m2.metric("Ganador Actual", totales.index[0], f"{int(totales.iloc[0])} votos")
        else:
            m2.metric("Ganador Actual", "N/A", "0 votos")
        
        # Cálculo de participación con protección de división por cero
        total_inscritos = pd.to_numeric(df_filtrado['Inscritos'], errors='coerce').sum()
        total_validos = pd.to_numeric(df_filtrado['Votos_Validos'], errors='coerce').sum()
        
        participacion = (total_validos / total_inscritos * 100) if total_inscritos > 0 else 0
        m3.metric("Participación", f"{participacion:.2f}%")

        # --- GRÁFICO EN AMARILLO (Usando Altair) ---
        df_chart = totales.reset_index()
        df_chart.columns = ['Partido', 'Votos']
        
        grafico = alt.Chart(df_chart).mark_bar(
            color='#FFD700' # Color amarillo/dorado
        ).encode(
            x=alt.X('Partido', sort=None, title='Partido/Sigla'),
            y=alt.Y('Votos', title='Total Votos'),
            tooltip=['Partido', 'Votos']
        ).properties(
            title=f"Votación por Partido"
        ).interactive()
        
        st.altair_chart(grafico, use_container_width=True)

    else:
        st.warning("No hay registros que coincidan con la combinación de filtros seleccionada.")

# --- 3. SEGURIDAD Y CONFIGURACIÓN ---
# Nota: Asegúrate de tener configurado .streamlit/secrets.toml
try:
    config = st.secrets.to_dict()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    authenticator.login(location='main')
except Exception as e:
    st.error(f"Error de configuración de seguridad. Verifique secrets.toml. Error: {e}")
    st.stop()

# --- 4. LÓGICA DE LA APLICACIÓN ---
if st.session_state["authentication_status"]:
    username = st.session_state["username"]
    user_role = config['credentials']['usernames'][username].get('role', 'editor') # Por defecto editor si no hay rol
    
    DB_FILE = "votos_C6-TecnicoAyacucho.csv"
    FOTOS_DIR = "fotosactas"
    if not os.path.exists(FOTOS_DIR): os.makedirs(FOTOS_DIR)

    df_mapeo, df_partidos = cargar_datos_maestros()
    CATEGORIAS = ["Gobernador", "Asambleísta Departamental", "Asambleísta Regional", "Alcalde", "Concejal"]

    # Carga de datos optimizada (una sola vez por ejecución)
    df_votos_actual = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()

    c_tit, c_logout = st.columns([5,1])
    with c_tit:
        st.title(f"🗳️ Captura de Actas - Alianza Patria Sol (Usuario: {username})")
    with c_logout:
        authenticator.logout('Cerrar Sesión', 'main')

    if df_mapeo.empty:
        st.error("Error: No se encontró archivo recintos.csv o está vacío.")
        st.stop()
    
    # --- CABECERA DINÁMICA ---
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1:
        circ_list = sorted(df_mapeo['circunscripcion'].unique().tolist())
        circ_sel = st.selectbox("Circunscripción", circ_list)
    with c2:
        df_rec = df_mapeo[df_mapeo['circunscripcion'] == circ_sel]
        rec_list = sorted(df_rec['NombreDeRecinto'].unique().tolist())
        recinto_sel = st.selectbox("Recinto", rec_list)
    with c3:
        df_mes = df_rec[df_rec['NombreDeRecinto'] == recinto_sel]
        mes_list = sorted(df_mes['mesa'].unique().tolist())
        mesa_sel = st.selectbox("Nro Mesa", mes_list)
    with c4:
        filtro_mesa = df_mes[df_mes['mesa'] == mesa_sel]
        if not filtro_mesa.empty:
            hab_val = filtro_mesa['NroHabilitados'].values[0]
            st.number_input("Habilitados", value=int(hab_val), disabled=True)
        else:
            hab_val = 0
            st.error("Mesa no encontrada")

    st.divider()

    # --- 5. BUCLE DE CATEGORÍAS ---
    for cat in CATEGORIAS:
        bloqueo = esta_bloqueado_optimizado(df_votos_actual, recinto_sel, mesa_sel, cat)        
        color = "red" if bloqueo else "blue"
        st.markdown(f"### 📍 Elección: :{color}[{cat.upper()}]")
        
        # --- NUEVO: RECUPERAR DATOS GUARDADOS ---
        datos_existentes = pd.DataFrame()
        if bloqueo and not df_votos_actual.empty:
            datos_existentes = df_votos_actual[(df_votos_actual['Recinto'] == recinto_sel) & 
                                               (df_votos_actual['Mesa'].astype(str) == str(mesa_sel)) & 
                                               (df_votos_actual['Categoría'] == cat)]
        
        # Variables por defecto (0 o vacío)
        def_v_val = 0
        def_obs = ""
        
        # Si hay datos guardados, actualizamos las variables por defecto
        if not datos_existentes.empty:
            fila = datos_existentes.iloc[0]
            def_v_val = int(fila.get("Votos_Validos", 0)) if pd.notna(fila.get("Votos_Validos")) else 0
            obs_texto = str(fila.get("Obs", ""))
            def_obs = obs_texto if obs_texto.lower() != 'nan' else ""

        # Lógica de permisos de edición
        deshabilitar_campos = bloqueo and user_role != 'admin'
        
        if bloqueo:
            if user_role != 'admin':
                st.warning(f"🔒 Acta de {cat} ya registrada. Mostrando en modo solo lectura.")
            else:
                st.info(f"🔓 Modo Administrador: Editando acta registrada de {cat}.")

        with st.form(key=f"form_{cat}_{mesa_sel}"):
            f1, f2 = st.columns([2, 1])
            with f1:
                foto = st.file_uploader(f"📸 Foto Acta {cat} (Opcional)", type=['jpg','png','jpeg'], key=f"img_{cat}", disabled=deshabilitar_campos)
            with f2:
                # Asignamos el valor guardado (def_v_val) al campo
                v_val = st.number_input(f"Votos Válidos ({cat})", min_value=0, value=def_v_val, key=f"val_{cat}", disabled=deshabilitar_campos)

            votos_data = {}
            if not df_partidos.empty:
                lista_candidatos = df_partidos.to_dict('records')
                lista_candidatos.extend([{'Sigla': 'Blancos', 'logo': ''}, {'Sigla': 'Nulos', 'logo': ''}])
                
                columnas_por_fila = 7
                for i in range(0, len(lista_candidatos), columnas_por_fila):
                    cols = st.columns(columnas_por_fila)
                    subgrupo = lista_candidatos[i : i + columnas_por_fila]
                    for j, cand in enumerate(subgrupo):
                        with cols[j]:
                            sigla = cand['Sigla']
                            nombre_archivo = str(cand.get('logo', ''))
                            ruta_logo = os.path.join("logos", nombre_archivo)
                           
                            if nombre_archivo and os.path.exists(ruta_logo):
                                st.image(ruta_logo, width=30)
                            
                            nombre_cand = str(cand.get('Nombre Candidato', ''))
                            if nombre_cand.lower() == 'nan' or nombre_cand.strip() == '':
                                st.caption(f"**{sigla}**")
                            else:
                                st.caption(f"**{sigla}** - {nombre_cand}")
                                
                            # --- NUEVO: Extraer votos guardados para este partido específico ---
                            valor_guardado_partido = 0
                            if not datos_existentes.empty and sigla in datos_existentes.columns:
                                val_partido = datos_existentes.iloc[0][sigla]
                                valor_guardado_partido = int(val_partido) if pd.notna(val_partido) else 0

                            # Asignamos el valor al input
                            v_input = st.number_input(label=sigla, min_value=0, value=valor_guardado_partido, key=f"v_{cat}_{sigla}_{mesa_sel}", label_visibility="collapsed", disabled=deshabilitar_campos)
                            votos_data[sigla] = v_input

            obs = st.text_input("Observaciones", value=def_obs, key=f"obs_{cat}", disabled=deshabilitar_campos)
            submit = st.form_submit_button(f"💾 GUARDAR ACTA {cat.upper()}", disabled=deshabilitar_campos)

            if submit:
                path_foto = "Sin Acta"
                if foto is not None:
                    nombre_seguro = f"{cat}_{recinto_sel}_{mesa_sel}".replace(" ","_").replace("/","")
                    path_foto = os.path.join(FOTOS_DIR, f"{nombre_seguro}.jpg")
                    try:
                        with open(path_foto, "wb") as f: 
                            f.write(foto.getbuffer())
                    except Exception as e:
                        st.error(f"Error guardando imagen: {e}")
                        st.stop()
                
                nuevo_reg = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Usuario": username, "Circunscripcion": circ_sel, "Recinto": recinto_sel, 
                    "Mesa": mesa_sel, "Categoría": cat, "Inscritos": hab_val, 
                    "Votos_Validos": v_val, "Foto": path_foto, **votos_data, "Obs": obs
                }
                
                df_nuevo = pd.DataFrame([nuevo_reg])
                
                try:
                    if bloqueo and user_role == 'admin':
                        df_db = pd.read_csv(DB_FILE)
                        df_db['Mesa'] = df_db['Mesa'].astype(str)
                        
                        filtro_borrar = ~((df_db['Recinto'] == recinto_sel) & 
                                         (df_db['Mesa'] == str(mesa_sel)) & 
                                         (df_db['Categoría'] == cat))
                        
                        df_db_actualizado = df_db[filtro_borrar]
                        df_final = pd.concat([df_db_actualizado, df_nuevo], ignore_index=True)
                        df_final.to_csv(DB_FILE, index=False)
                        st.success(f"✅ Acta de {cat} actualizada por Administrador.")
                    else:
                        header_exist = os.path.exists(DB_FILE)
                        df_nuevo.to_csv(DB_FILE, mode='a', header=not header_exist, index=False)
                        st.success(f"✅ Acta de {cat} guardada exitosamente.")
                    
                    import time
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error al guardar en base de datos: {e}")
    # --- 6. PANEL DE CONTROL ADMIN ---
    # Recargamos df_votos_actual para reflejar cambios si los hubo en esta ejecución
    df_votos_final = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()

    if user_role == 'admin' and not df_votos_final.empty:
        st.divider()
        st.header("📊 Panel de Control de Datos (Administrador)")
        
        with st.expander("Ver Base de Datos Completa"):
            st.dataframe(df_votos_final)
            st.download_button("📥 Descargar CSV", df_votos_final.to_csv(index=False), "votos_patria_sol_completo.csv", "text/csv")
        
        generar_reporte_votos(df_votos_final)

elif st.session_state["authentication_status"] is False:
    st.error('Usuario/Contraseña incorrectos')
elif st.session_state["authentication_status"] is None:
    st.info('Por favor ingrese sus credenciales')