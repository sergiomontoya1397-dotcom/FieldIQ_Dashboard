import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("🌱 Dashboard de Fertilización")

# Datos ejemplo
data = {
    "Rango": ["Sub-aplicado", "Óptimo", "Sobre-aplicado"],
    "Área": [0.931, 5.356, 27.862]
}

df = pd.DataFrame(data)

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric("Sub-aplicado", "0.931 ha")
col2.metric("Óptimo", "5.356 ha")
col3.metric("Sobre-aplicado", "27.862 ha")

# Gráfico
fig = px.pie(
    df,
    values="Área",
    names="Rango",
    color="Rango",
    color_discrete_map={
        "Sub-aplicado":"red",
        "Óptimo":"yellow",
        "Sobre-aplicado":"green"
    }
)

st.plotly_chart(fig, use_container_width=True)

# Tabla
st.dataframe(df)
archivo = st.file_uploader("Sube tu shapefile en .zip", type=["zip"])
