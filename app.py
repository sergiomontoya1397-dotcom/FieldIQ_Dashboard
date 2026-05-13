import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import tempfile
import zipfile
import os

st.set_page_config(layout="wide")

st.title("🌱 Dashboard de Fertilización")

# Parámetros
objetivo = st.sidebar.number_input(
    "Dosis objetivo",
    value=150
)

tolerancia = st.sidebar.slider(
    "Tolerancia %",
    1,
    20,
    5
)

uploaded_file = st.file_uploader(
    "Sube tu shapefile en .zip",
    type=["zip"]
)

if uploaded_file:

    temp_dir = tempfile.mkdtemp()

    zip_path = os.path.join(temp_dir, uploaded_file.name)

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_file = None

    for file in os.listdir(temp_dir):
        if file.endswith(".shp"):
            shp_file = os.path.join(temp_dir, file)

    if shp_file:

        gdf = gpd.read_file(shp_file, engine="pyogrio")

        st.success("Shapefile cargado correctamente")

        # reproyectar para área
        gdf = gdf.to_crs(epsg=3857)

        # área en hectáreas
        gdf["Area_ha"] = gdf.geometry.area / 10000

        # límites
        min_ok = objetivo * (1 - tolerancia/100)
        max_ok = objetivo * (1 + tolerancia/100)

        # clasificar
        def clasificar(valor):

            if valor < min_ok:
                return "Sub-aplicado"

            elif valor <= max_ok:
                return "Óptimo"

            else:
                return "Sobre-aplicado"

        gdf["Categoria"] = gdf["AppliedRat"].apply(clasificar)

        resumen = (
            gdf.groupby("Categoria")["Area_ha"]
            .sum()
            .reset_index()
        )

        total = resumen["Area_ha"].sum()

        resumen["Porcentaje"] = (
            resumen["Area_ha"] / total * 100
        )

        # KPIs
        col1, col2, col3 = st.columns(3)

        for _, row in resumen.iterrows():

            if row["Categoria"] == "Sub-aplicado":
                col1.metric(
                    "Sub-aplicado",
                    f"{row['Area_ha']:.2f} ha"
                )

            elif row["Categoria"] == "Óptimo":
                col2.metric(
                    "Óptimo",
                    f"{row['Area_ha']:.2f} ha"
                )

            else:
                col3.metric(
                    "Sobre-aplicado",
                    f"{row['Area_ha']:.2f} ha"
                )

        # gráfico
        fig = px.pie(
            resumen,
            values="Area_ha",
            names="Categoria",
            color="Categoria",
            color_discrete_map={
                "Sub-aplicado":"red",
                "Óptimo":"yellow",
                "Sobre-aplicado":"green"
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # tabla
        st.dataframe(resumen)

    else:
        st.error("No se encontró archivo .shp")
