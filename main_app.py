"""
Dashboard Mundial - Streamlit + Plotly
----------------------------------------
Dashboard interactivo con datos sintéticos de partidos de un Mundial de fútbol.
Incluye:
  1. Generación/simulación de datos sintéticos (100 registros x 8 columnas, tipos mixtos)
  2. Esquema de métricas cuantitativas y cualitativas
  3. Gráficas dinámicas con Plotly
  4. Personalización: el usuario elige variables, tipo de gráfica, colores, agregaciones
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Mundial",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------------------
# 1. INGESTA / SIMULACIÓN DE DATOS SINTÉTICOS
#    8 columnas con tipos distintos:
#      - Equipo_Local        -> categórica (texto)
#      - Equipo_Visitante    -> categórica (texto)
#      - Fase                -> categórica ordinal (texto)
#      - Fecha                -> fecha (datetime)
#      - Goles_Local          -> entero
#      - Goles_Visitante      -> entero
#      - Asistencia           -> entero (grande, numérico continuo)
#      - Posesion_Local_pct   -> flotante (porcentaje)
# --------------------------------------------------------------------------------------

EQUIPOS = [
    "Argentina", "Brasil", "Francia", "Alemania", "España", "Inglaterra",
    "Portugal", "Países Bajos", "Croacia", "Uruguay", "Colombia", "México",
    "Marruecos", "Japón", "Estados Unidos", "Bélgica",
]

FASES = ["Grupos", "Octavos", "Cuartos", "Semifinal", "Final"]
FASE_ORDEN = {f: i for i, f in enumerate(FASES)}


@st.cache_data(show_spinner=False)
def generar_datos(n_registros: int, semilla: int) -> pd.DataFrame:
    """Simula un dataset de partidos de un Mundial de fútbol."""
    rng = np.random.default_rng(semilla)

    equipos_local = rng.choice(EQUIPOS, size=n_registros)
    # Aseguramos que el visitante nunca sea igual al local
    equipos_visitante = []
    for local in equipos_local:
        opciones = [e for e in EQUIPOS if e != local]
        equipos_visitante.append(rng.choice(opciones))

    fases = rng.choice(FASES, size=n_registros, p=[0.55, 0.22, 0.13, 0.07, 0.03])
    fechas = pd.to_datetime("2026-06-11") + pd.to_timedelta(
        rng.integers(0, 32, size=n_registros), unit="D"
    )

    goles_local = rng.poisson(lam=1.3, size=n_registros)
    goles_visitante = rng.poisson(lam=1.1, size=n_registros)

    asistencia = rng.integers(28000, 88000, size=n_registros)
    posesion_local = np.clip(rng.normal(50, 10, size=n_registros), 22, 78).round(1)

    df = pd.DataFrame(
        {
            "Equipo_Local": equipos_local,
            "Equipo_Visitante": equipos_visitante,
            "Fase": fases,
            "Fecha": fechas,
            "Goles_Local": goles_local,
            "Goles_Visitante": goles_visitante,
            "Asistencia": asistencia,
            "Posesion_Local_pct": posesion_local,
        }
    )

    df = df.sort_values("Fecha").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------------------
# SIDEBAR: CONTROLES DE SIMULACIÓN Y PERSONALIZACIÓN
# --------------------------------------------------------------------------------------
st.sidebar.title("⚙️ Configuración")

st.sidebar.subheader("1. Simulación de datos")
n_registros = st.sidebar.slider("Número de registros", min_value=20, max_value=300, value=100, step=10)
semilla = st.sidebar.number_input("Semilla aleatoria", min_value=0, max_value=9999, value=42, step=1)
if st.sidebar.button("🔄 Regenerar datos"):
    st.cache_data.clear()

df = generar_datos(n_registros, semilla)

# Columnas derivadas útiles para el análisis (no cuentan dentro de las 8 originales)
df["Diferencia_Goles"] = df["Goles_Local"] - df["Goles_Visitante"]
df["Total_Goles"] = df["Goles_Local"] + df["Goles_Visitante"]
df["Resultado"] = np.select(
    [df["Diferencia_Goles"] > 0, df["Diferencia_Goles"] < 0],
    ["Gana Local", "Gana Visitante"],
    default="Empate",
)

columnas_numericas = df.select_dtypes(include=np.number).columns.tolist()
columnas_categoricas = df.select_dtypes(include="object").columns.tolist()
columnas_fecha = df.select_dtypes(include="datetime").columns.tolist()

st.sidebar.subheader("2. Filtros")
fases_sel = st.sidebar.multiselect("Fase", options=FASES, default=FASES)
equipos_sel = st.sidebar.multiselect("Equipo (local o visitante)", options=sorted(EQUIPOS), default=[])

df_filtrado = df[df["Fase"].isin(fases_sel)].copy()
if equipos_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Equipo_Local"].isin(equipos_sel) | df_filtrado["Equipo_Visitante"].isin(equipos_sel)
    ]

# --------------------------------------------------------------------------------------
# ENCABEZADO
# --------------------------------------------------------------------------------------
st.title("⚽ Dashboard Mundial — Datos Sintéticos")
st.caption(
    "Datos simulados dentro de la plataforma (no reales). Ajusta la simulación y los filtros "
    "en la barra lateral, y personaliza las gráficas más abajo."
)

# --------------------------------------------------------------------------------------
# 2. ESQUEMA DE MÉTRICAS
# --------------------------------------------------------------------------------------
st.header("📊 Métricas generales")

if df_filtrado.empty:
    st.warning("No hay registros con los filtros seleccionados. Ajusta la fase o los equipos.")
else:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Partidos", len(df_filtrado))
    c2.metric("Goles promedio/partido", f"{df_filtrado['Total_Goles'].mean():.2f}")
    c3.metric("Asistencia promedio", f"{df_filtrado['Asistencia'].mean():,.0f}")
    c4.metric("Posesión local promedio", f"{df_filtrado['Posesion_Local_pct'].mean():.1f}%")
    equipo_mas_local = df_filtrado["Equipo_Local"].mode().iat[0] if not df_filtrado["Equipo_Local"].mode().empty else "-"
    c5.metric("Equipo local más frecuente", equipo_mas_local)

    tab_cuanti, tab_cuali, tab_tabla = st.tabs(
        ["🔢 Estadística cuantitativa", "🔤 Estadística cualitativa", "🧾 Datos crudos"]
    )

    with tab_cuanti:
        st.subheader("Resumen descriptivo de variables numéricas")
        st.dataframe(df_filtrado[columnas_numericas].describe().T, use_container_width=True)

        st.subheader("Matriz de correlación")
        corr = df_filtrado[columnas_numericas].corr(numeric_only=True)
        fig_corr = px.imshow(
            corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
            title="Correlación entre variables numéricas",
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    with tab_cuali:
        st.subheader("Frecuencias de variables categóricas")
        col_cat = st.selectbox("Selecciona una variable categórica", options=columnas_categoricas + ["Resultado"])
        conteo = df_filtrado[col_cat].value_counts().reset_index()
        conteo.columns = [col_cat, "Frecuencia"]
        conteo["Porcentaje_%"] = (conteo["Frecuencia"] / conteo["Frecuencia"].sum() * 100).round(1)
        st.dataframe(conteo, use_container_width=True)

        fig_cuali = px.pie(conteo, names=col_cat, values="Frecuencia", title=f"Distribución de {col_cat}", hole=0.35)
        st.plotly_chart(fig_cuali, use_container_width=True)

    with tab_tabla:
        st.dataframe(df_filtrado, use_container_width=True)
        st.download_button(
            "⬇️ Descargar datos filtrados (CSV)",
            data=df_filtrado.to_csv(index=False).encode("utf-8"),
            file_name="datos_mundial_filtrados.csv",
            mime="text/csv",
        )

    # ----------------------------------------------------------------------------------
    # 3 y 4. GRÁFICAS DINÁMICAS Y PERSONALIZABLES
    # ----------------------------------------------------------------------------------
    st.header("🎨 Gráficas dinámicas personalizables")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        tipo_grafica = st.selectbox(
            "Tipo de gráfica",
            ["Barras", "Líneas", "Dispersión", "Histograma", "Caja (Box)", "Violín"],
        )
    with col_b:
        eje_x = st.selectbox("Variable eje X", options=df_filtrado.columns.tolist(), index=df_filtrado.columns.get_loc("Fase"))
    with col_c:
        opciones_y = ["(ninguna)"] + columnas_numericas
        eje_y = st.selectbox("Variable eje Y", options=opciones_y, index=opciones_y.index("Total_Goles") if "Total_Goles" in opciones_y else 0)

    col_d, col_e, col_f = st.columns(3)
    with col_d:
        color_por = st.selectbox("Color por", options=["(ninguno)"] + columnas_categoricas + ["Resultado"])
    with col_e:
        agregacion = st.selectbox("Agregación (barras/líneas)", ["suma", "promedio", "conteo", "máximo", "mínimo"])
    with col_f:
        paleta = st.selectbox(
            "Paleta de colores",
            ["Plotly", "Vivid", "Bold", "Pastel", "Set2", "Dark24"],
        )

    mapa_paletas = {
        "Plotly": px.colors.qualitative.Plotly,
        "Vivid": px.colors.qualitative.Vivid,
        "Bold": px.colors.qualitative.Bold,
        "Pastel": px.colors.qualitative.Pastel,
        "Set2": px.colors.qualitative.Set2,
        "Dark24": px.colors.qualitative.Dark24,
    }
    secuencia_color = mapa_paletas[paleta]
    color_arg = None if color_por == "(ninguno)" else color_por

    def agregar(df_in, x, y, func):
        mapa_func = {"suma": "sum", "promedio": "mean", "conteo": "count", "máximo": "max", "mínimo": "min"}
        agrupador = [x] if color_arg is None else [x, color_arg]
        return df_in.groupby(agrupador, as_index=False)[y].agg(mapa_func[func])

    fig = None
    try:
        if tipo_grafica == "Barras":
            if eje_y == "(ninguna)":
                datos_plot = df_filtrado.groupby([eje_x] + ([color_arg] if color_arg else []), as_index=False).size()
                fig = px.bar(datos_plot, x=eje_x, y="size", color=color_arg, color_discrete_sequence=secuencia_color,
                             title=f"Conteo de registros por {eje_x}")
            else:
                datos_plot = agregar(df_filtrado, eje_x, eje_y, agregacion)
                fig = px.bar(datos_plot, x=eje_x, y=eje_y, color=color_arg, color_discrete_sequence=secuencia_color,
                             title=f"{agregacion.capitalize()} de {eje_y} por {eje_x}", barmode="group")

        elif tipo_grafica == "Líneas":
            y_linea = eje_y if eje_y != "(ninguna)" else columnas_numericas[0]
            datos_plot = df_filtrado.sort_values(eje_x)
            fig = px.line(datos_plot, x=eje_x, y=y_linea, color=color_arg, color_discrete_sequence=secuencia_color,
                          markers=True, title=f"Evolución de {y_linea} sobre {eje_x}")

        elif tipo_grafica == "Dispersión":
            y_disp = eje_y if eje_y != "(ninguna)" else columnas_numericas[0]
            fig = px.scatter(df_filtrado, x=eje_x, y=y_disp, color=color_arg, color_discrete_sequence=secuencia_color,
                             size="Asistencia" if "Asistencia" in df_filtrado.columns else None,
                             hover_data=["Equipo_Local", "Equipo_Visitante"],
                             title=f"{y_disp} vs {eje_x}")

        elif tipo_grafica == "Histograma":
            var_hist = eje_y if eje_y != "(ninguna)" else eje_x
            fig = px.histogram(df_filtrado, x=var_hist, color=color_arg, color_discrete_sequence=secuencia_color,
                               title=f"Distribución de {var_hist}", nbins=20)

        elif tipo_grafica == "Caja (Box)":
            y_box = eje_y if eje_y != "(ninguna)" else columnas_numericas[0]
            fig = px.box(df_filtrado, x=eje_x, y=y_box, color=color_arg, color_discrete_sequence=secuencia_color,
                        title=f"Distribución de {y_box} por {eje_x}")

        elif tipo_grafica == "Violín":
            y_vio = eje_y if eje_y != "(ninguna)" else columnas_numericas[0]
            fig = px.violin(df_filtrado, x=eje_x, y=y_vio, color=color_arg, color_discrete_sequence=secuencia_color,
                            box=True, title=f"Distribución de {y_vio} por {eje_x}")

        if fig is not None:
            fig.update_layout(legend_title_text=color_por if color_arg else "")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"No fue posible construir la gráfica con esta combinación de variables: {e}")

    st.divider()
    st.subheader("📈 Comparación rápida entre dos variables numéricas")
    col_g, col_h = st.columns(2)
    with col_g:
        var1 = st.selectbox("Variable numérica 1", options=columnas_numericas, index=0, key="var1")
    with col_h:
        var2 = st.selectbox("Variable numérica 2", options=columnas_numericas, index=1 if len(columnas_numericas) > 1 else 0, key="var2")

    fig_comp = px.scatter(
        df_filtrado, x=var1, y=var2, color="Fase",
        color_discrete_sequence=px.colors.qualitative.Set2,
        title=f"Relación entre {var1} y {var2}",
    )

    # Línea de tendencia calculada manualmente (regresión lineal simple con NumPy),
    # para no depender de statsmodels (evita problemas de instalación en Python 3.14).
    datos_validos = df_filtrado[[var1, var2]].dropna()
    if len(datos_validos) >= 2:
        pendiente, intercepto = np.polyfit(datos_validos[var1], datos_validos[var2], 1)
        x_linea = np.linspace(datos_validos[var1].min(), datos_validos[var1].max(), 100)
        y_linea = pendiente * x_linea + intercepto
        fig_comp.add_scatter(
            x=x_linea, y=y_linea, mode="lines", name="Tendencia (regresión lineal)",
            line=dict(color="black", dash="dash"),
        )

    st.plotly_chart(fig_comp, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Datos 100% sintéticos, generados con NumPy dentro de la app para fines demostrativos.")
