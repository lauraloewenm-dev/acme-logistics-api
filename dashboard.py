import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Acme Logistics Dashboard", layout="wide")

st.title("📊 Acme Logistics - Call Analytics")

API_URL = "https://acme-logistics-api-production.up.railway.app/get-logs"

try:
    response = requests.get(API_URL)
    data = response.json()
    
    # --- ESCUDO DE DEPURACIÓN ---
    # Si la API nos devuelve un diccionario (error o mensaje) en lugar de una lista
    if isinstance(data, dict):
        st.warning(f"⚠️ La API no devolvió una lista de llamadas. Respondió esto: {data}")
    
    # Si la API devuelve una lista vacía
    elif not data:
        st.info("No hay llamadas registradas todavía. ¡Haz una llamada de prueba con Laura!")
        
    # Si la API devuelve los datos correctamente
    else:
        df = pd.DataFrame(data)
        
        # --- MÉTRICAS SUPERIORES ---
        col1, col2, col3 = st.columns(3)
        total_calls = len(df)
        booked_calls = len(df[df['call_outcome'] == 'Booked'])
        
        col1.metric("Total Llamadas", total_calls)
        col2.metric("Tasa de Conversión", f"{(booked_calls/total_calls)*100:.0f}%" if total_calls > 0 else "0%")
        col3.metric("Sentimiento Positivo", f"{len(df[df['carrier_sentiment'] == 'Positive'])}")

        st.markdown("---")
        
        # --- GRÁFICOS Y TABLAS ---
        col_chart, col_table = st.columns([1, 2])
        
        with col_chart:
            st.subheader("Resultados de Llamada")
            outcome_counts = df['call_outcome'].value_counts()
            st.bar_chart(outcome_counts)
            
        with col_table:
            st.subheader("Registro Detallado")
            st.dataframe(df[['timestamp', 'carrier_name', 'call_outcome', 'agreed_rate', 'carrier_sentiment']])
            
except Exception as e:
    st.error(f"Error crítico conectando con la API: {e}")
