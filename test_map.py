import streamlit as st
from streamlit_folium import st_folium
import folium
m = folium.Map(location=[30, 0], zoom_start=3)
st.title("Map Test")
st_folium(m, width=700, height=500)
