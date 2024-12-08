import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# Configuración de la página
st.set_page_config(
    page_title="Real Estate Analytics",
    page_icon="🏠",
    layout="wide"
)

# Función para la conexión a la base de datos
@st.cache_resource
def get_database_connection():
    credentials = st.secrets["postgres"]
    connection_string = (
        f"postgresql://{credentials['user']}:{credentials['password']}@"
        f"{credentials['host']}:{credentials['port']}/{credentials['database']}"
    )
    try:
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {str(e)}")
        return None

# Función para cargar datos
@st.cache_data
def load_data():
    engine = get_database_connection()
    if engine is None:
        return pd.DataFrame()
    try:
        return pd.read_sql('SELECT * FROM properties', engine)
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame()

[... resto del código del dashboard ...]