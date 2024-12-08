import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Real Estate Analytics",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .metric-card {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        text-align: center;
    }
    .big-number {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

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
        df = pd.read_sql('SELECT * FROM properties', engine)
        # Convertir coordenadas a lat/lon
        df[['lat', 'lon']] = df['coordinates'].str.split(',', expand=True).astype(float)
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame()

# Cargar datos
df = load_data()

# Sidebar con filtros
st.sidebar.title("Filtros")

# Filtros
comarca = st.sidebar.selectbox(
    "Comarca",
    options=["Todas"] + sorted(df['comarca'].unique().tolist())
)

ocupacion = st.sidebar.multiselect(
    "Estado de Ocupación",
    options=sorted(df['occupancy'].unique().tolist()),
    default=sorted(df['occupancy'].unique().tolist())
)

price_range = st.sidebar.slider(
    "Rango de Precio (¥)",
    min_value=float(df['price'].min()),
    max_value=float(df['price'].max()),
    value=(float(df['price'].min()), float(df['price'].max())),
    format="%.0f"
)

# Aplicar filtros
mask = df['price'].between(price_range[0], price_range[1])
mask &= df['occupancy'].isin(ocupacion)
if comarca != "Todas":
    mask &= (df['comarca'] == comarca)

filtered_df = df[mask]

# Título principal
st.title("🏠 Análisis de Propiedades Inmobiliarias")

# Métricas principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Precio Promedio",
        f"¥{filtered_df['price'].mean():,.0f}",
        f"{filtered_df['price'].mean() / df['price'].mean() - 1:+.1%}"
    )

with col2:
    st.metric(
        "Rentabilidad Media",
        f"{filtered_df['rentability_index'].mean():.2%}",
        f"{filtered_df['rentability_index'].mean() / df['rentability_index'].mean() - 1:+.1%}"
    )

with col3:
    st.metric(
        "Propiedades",
        f"{len(filtered_df):,}",
        f"{len(filtered_df) / len(df) - 1:+.1%}"
    )

with col4:
    st.metric(
        "Periodo de Recuperación",
        f"{filtered_df['payback_period'].mean():.1f} años",
        f"{filtered_df['payback_period'].mean() / df['payback_period'].mean() - 1:+.1%}"
    )

# Gráficos
st.header("Análisis de Mercado")

tab1, tab2, tab3 = st.tabs(["Distribución", "Correlaciones", "Mapa"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución de precios
        fig_price = px.histogram(
            filtered_df,
            x="price",
            nbins=50,
            title="Distribución de Precios",
            labels={"price": "Precio (¥)", "count": "Cantidad"}
        )
        fig_price.update_layout(showlegend=False)
        st.plotly_chart(fig_price, use_container_width=True)
    
    with col2:
        # Distribución de rentabilidad
        fig_rent = px.histogram(
            filtered_df,
            x="rentability_index",
            nbins=50,
            title="Distribución de Rentabilidad",
            labels={"rentability_index": "Índice de Rentabilidad", "count": "Cantidad"}
        )
        fig_rent.update_layout(showlegend=False)
        st.plotly_chart(fig_rent, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # Rentabilidad vs Precio
        fig_scatter = px.scatter(
            filtered_df,
            x="price",
            y="rentability_index",
            color="occupancy",
            title="Rentabilidad vs Precio",
            labels={
                "price": "Precio (¥)", 
                "rentability_index": "Índice de Rentabilidad",
                "occupancy": "Ocupación"
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        # Precio por m²
        fig_size = px.scatter(
            filtered_df,
            x="size",
            y="price",
            color="occupancy",
            title="Precio vs Tamaño",
            labels={
                "size": "Tamaño (m²)", 
                "price": "Precio (¥)",
                "occupancy": "Ocupación"
            }
        )
        st.plotly_chart(fig_size, use_container_width=True)

with tab3:
    # Mapa de propiedades
    st.header("Ubicación de Propiedades")
    
    fig_map = px.scatter_mapbox(
        filtered_df,
        lat='lat',
        lon='lon',
        color='rentability_index',
        size='price',
        hover_name='address',
        hover_data={
            'price': ':,.0f',
            'rentability_index': ':.2%',
            'payback_period': ':.1f',
            'lat': False,
            'lon': False
        },
        color_continuous_scale='Viridis',
        zoom=10,
        title="Mapa de Propiedades",
        mapbox_style="open-street-map"
    )
    
    fig_map.update_layout(
        height=600,
        mapbox=dict(
            center=dict(
                lat=filtered_df['lat'].mean(),
                lon=filtered_df['lon'].mean()
            )
        )
    )
    
    st.plotly_chart(fig_map, use_container_width=True)

# Tabla de datos detallados
st.header("Propiedades Detalladas")

# Selector de columnas
cols_to_show = st.multiselect(
    "Selecciona las columnas a mostrar",
    options=filtered_df.columns.tolist(),
    default=['address', 'price', 'size', 'rentability_index', 'payback_period', 'avg_annual_rev']
)

# Mostrar tabla con formato
st.dataframe(
    filtered_df[cols_to_show].style.format({
        'price': '{:,.0f}',
        'rentability_index': '{:.2%}',
        'payback_period': '{:.1f}',
        'avg_annual_rev': '{:,.0f}'
    }),
    hide_index=True,
    use_container_width=True
)

# Footer con información adicional
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>Datos actualizados: Último procesamiento</small>
</div>
""", unsafe_allow_html=True)