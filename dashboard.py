import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

# Page Config
st.set_page_config(page_title="Study Results Dashboard", layout="wide")

st.title("Study Results Explorer")

OUTPUT_FILE = "output.csv"

def load_data():
    if not os.path.exists(OUTPUT_FILE):
        return None
    try:
        return pd.read_csv(OUTPUT_FILE)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

# Auto-refresh logic (optional)
if st.checkbox("Auto-refresh data (every 2s)", value=True):
    time.sleep(2)
    st.rerun()

df = load_data()

if df is not None and not df.empty:
    st.sidebar.header("Plot Configuration")
    
    # Get all columns (inputs + outputs)
    columns = df.columns.tolist()
    
    # Sidebar Dropdowns
    x_axis = st.sidebar.selectbox("Select X Axis", options=columns, index=0)
    # Default Y to the last column (likely an output)
    y_axis = st.sidebar.selectbox("Select Y Axis", options=columns, index=len(columns)-1)
    
    color_by = st.sidebar.selectbox("Color By (Optional)", options=["None"] + columns, index=0)

    # Main Area Plot
    st.subheader(f"{y_axis} vs {x_axis}")
    
    if color_by != "None":
        fig = px.scatter(df, x=x_axis, y=y_axis, color=color_by, title=f"Scatter Plot: {x_axis} vs {y_axis}")
    else:
        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"Scatter Plot: {x_axis} vs {y_axis}")
        
    st.plotly_chart(fig, use_container_width=True)

    # Show raw data table
    with st.expander("View Raw Data"):
        st.dataframe(df)
        
else:
    st.warning("Waiting for data... Ensure 'output.csv' exists and is being populated.")