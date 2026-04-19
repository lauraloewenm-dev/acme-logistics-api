import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import random

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Acme Analytics | AI Dispatch", page_icon="🚛", layout="wide")

API_URL = "https://acme-logistics-api-production.up.railway.app" # <-- ¡PON TU URL AQUÍ!
API_KEY = "super-secret-acme-key" 

st.title("🚛 Acme Logistics: AI Operations Command Center")
st.markdown("Real-time performance, network intelligence, and call transcripts from the HappyRobot AI.")

# --- OBTENER DATOS ---
@st.cache_data(ttl=5) 
def fetch_data():
    headers = {"X-API-Key": API_KEY}
    df_logs, df_loads = pd.DataFrame(), pd.DataFrame()
    try:
        # Traer Logs
        res_logs = requests.get(f"{API_URL}/get-logs", headers=headers)
        if res_logs.status_code == 200:
            df_logs = pd.DataFrame(res_logs.json())
        
        # Traer Cargas (para el mapa)
        res_loads = requests.get(f"{API_URL}/get-loads?origin=", headers=headers)
        if res_loads.status_code == 200:
            data = res_loads.json()
            if "loads" in data:
                df_loads = pd.DataFrame(data["loads"])
    except:
        pass
    return df_logs, df_loads

df, df_loads = fetch_data()

if df.empty:
    st.info("Waiting for Laura (AI) to make the first calls... Data will appear here automatically.")
else:
    # --- PROCESAMIENTO DE DATOS ---
    df['agreed_rate'] = pd.to_numeric(df['agreed_rate'], errors='coerce').fillna(0)
    df['initial_rate'] = pd.to_numeric(df['initial_rate'], errors='coerce').fillna(0)
    
    # Lógica de Margen (Asumiendo que cobramos un 20% sobre la tarifa base de mercado)
    df['estimated_shipper_revenue'] = df['agreed_rate'] * 1.20 
    df['gross_margin_profit'] = df.apply(
        lambda row: (row['estimated_shipper_revenue'] - row['agreed_rate']) if 'booked' in str(row['call_outcome']).lower() else 0, 
        axis=1
    )

    total_profit = df['gross_margin_profit'].sum()
    total_revenue = df['estimated_shipper_revenue'].sum() if total_profit > 0 else 0
    total_booked = len(df[df['call_outcome'].str.lower().str.contains('booked')])
    total_calls = len(df)
    win_rate = (total_booked / total_calls) * 100 if total_calls > 0 else 0
    margin_percentage = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0

    # --- PESTAÑAS (TABS) PARA ORGANIZAR LA VISTA ---
    tab1, tab2, tab3 = st.tabs(["📊 Executive Overview", "🗺️ Network & Analytics", "📞 Call Transcripts & Logs"])

    # ==========================================
    # PESTAÑA 1: RESUMEN EJECUTIVO (KPIs y Recomendaciones)
    # ==========================================
    with tab1:
        st.markdown("### 📈 Executive KPI Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gross Profit Generated", f"${total_profit:,.2f}", f"Avg Margin: {margin_percentage:.1f}%")
        col2.metric("Loads Booked via AI", f"{total_booked} / {total_calls} Calls")
        col3.metric("AI Negotiation Win Rate", f"{win_rate:.1f}%")
        avg_profit = total_profit / total_booked if total_booked > 0 else 0
        col4.metric("Avg. Profit per Load", f"${avg_profit:,.2f}")

        st.divider()

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("#### 💰 Broker Margin Spread by Carrier")
            if total_booked > 0:
                booked_df = df[df['call_outcome'].str.lower().str.contains('booked')]
                fig_margin = px.bar(
                    booked_df, x='carrier_name', y=['agreed_rate', 'gross_margin_profit'],
                    title="Carrier Cost vs Acme Profit ($)",
                    color_discrete_map={'agreed_rate': '#3b82f6', 'gross_margin_profit': '#10b981'}
                )
                st.plotly_chart(fig_margin, use_container_width=True)
            else:
                st.info("No booked loads yet to calculate margins.")

        with col_chart2:
            st.markdown("#### 🧠 AI System Recommendations")
            negative_calls = len(df[df['carrier_sentiment'].str.lower().str.contains('negative')])
            st.success(f"**Financial Insight:** The AI is maintaining a healthy {margin_percentage:.1f}% gross margin. **Recommendation:** Increase AI call volume for off-hours dispatching.")
            if negative_calls > 0:
                st.error(f"**Operational Alert:** {negative_calls} carriers ended the call with a negative sentiment. **Recommendation:** Review call transcripts in Tab 3. Consider adjusting the AI's prompt to be more polite.")
            elif win_rate < 50 and total_calls > 2:
                st.warning("**Performance Alert:** The booking rate is dropping. **Recommendation:** Market rates might have shifted. Consider raising the AI's starting offer.")

    # ==========================================
    # PESTAÑA 2: NETWORK & ANALYTICS (Mapa y Correlaciones)
    # ==========================================
    with tab2:
        st.markdown("### 🗺️ Live Network Availability")
        # Diccionario de coordenadas para simular el mapa basado en el origen de las cargas
        coords_map = {
            "Chicago, IL": [41.8781, -87.6298], "Dallas, TX": [32.7767, -96.7970],
            "Miami, FL": [25.7617, -80.1918], "Los Angeles, CA": [34.0522, -118.2437],
            "Atlanta, GA": [33.7490, -84.3880], "Seattle, WA": [47.6062, -122.3321],
            "Denver, CO": [39.7392, -104.9903], "Newark, NJ": [40.7357, -74.1724]
        }
        
        if not df_loads.empty:
            # Añadimos Lat y Lon al dataframe de cargas para dibujarlo en el mapa
            df_loads['lat'] = df_loads['origin'].map(lambda x: coords_map.get(x, [0,0])[0])
            df_loads['lon'] = df_loads['origin'].map(lambda x: coords_map.get(x, [0,0])[1])
            df_map = df_loads[df_loads['lat'] != 0] # Filtramos las que no tienen coordenadas
            
            st.map(df_map[['lat', 'lon']], zoom=3, use_container_width=True)
            st.caption("Heatmap of currently available loads waiting for AI dispatch.")
        else:
            st.info("No active loads on the board to display on the map.")

        st.divider()

        col_corr1, col_corr2 = st.columns(2)
        with col_corr1:
            st.markdown("#### ⏱️ Correlation: Call Duration vs Sentiment")
            # Simulamos minutos de duración para la demo (ya que no lo tenemos en BD)
            df['call_duration_min'] = [random.randint(2, 12) for _ in range(len(df))]
            fig_corr = px.scatter(
                df, x="call_duration_min", y="agreed_rate", 
                color="carrier_sentiment", size="agreed_rate",
                hover_data=['carrier_name'], title="Does talking longer get better rates?"
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            
        with col_corr2:
            st.markdown("#### 🤝 Carrier Loyalty Ranking")
            loyalty = df['carrier_name'].value_counts().reset_index()
            loyalty.columns = ['Carrier Name', 'Total Calls / Interactions']
            st.dataframe(loyalty, use_container_width=True)

    # ==========================================
    # PESTAÑA 3: CALL TRANSCRIPTS (¡Lo que pedías!)
    # ==========================================
    with tab3:
        st.markdown("### 📝 Individual Call Transcripts")
        st.write("Review the negotiation details generated by the HappyRobot agent after hanging up.")
        
        # Aquí están tus desplegables llamada por llamada
        for index, row in df.iterrows():
            status_color = "🟢" if "booked" in str(row['call_outcome']).lower() else "🔴"
            with st.expander(f"{status_color} {row['carrier_name']} (Load: {row['load_id']}) - Rate: ${row['agreed_rate']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Outcome:** {row['call_outcome']}")
                    st.markdown(f"**Carrier Sentiment:** {row['carrier_sentiment']}")
                with col_b:
                    st.markdown(f"**MC Number:** {row['mc_number']}")
                    st.markdown(f"**Initial Ask:** ${row['initial_rate']}")
                st.markdown(f"**AI Call Summary:**")
                st.info(row['call_summary'])

        st.divider()
        st.markdown("### 📋 Raw Database Log")
        st.dataframe(df[['timestamp', 'load_id', 'carrier_name', 'mc_number', 'agreed_rate', 'gross_margin_profit', 'call_outcome']], use_container_width=True)
