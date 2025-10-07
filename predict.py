import streamlit as st
import pandas as pd
import plotly.express as px

# Load CSV
df = pd.read_csv('final1.csv')

# ------------------------ Sidebar Filters ------------------------
st.sidebar.header("Filters")

# Region filter
regions = df['region'].unique()
selected_regions = st.sidebar.multiselect("Select Region(s)", options=regions, default=regions.tolist())

# Category filter
categories = df['categories'].unique()
selected_categories = st.sidebar.multiselect("Select Category(s)", options=categories, default=categories.tolist())

# Number of top items to show per region
top_n = st.sidebar.slider("Number of top items to show per region", min_value=3, max_value=10, value=5)

# Table columns selection
st.sidebar.subheader("Select Table Columns")
all_columns = ['No', 'Itemcode', 'Total Sold (Qty)', 'Total Value (Rs)', 'Next Month Forecast (Qty)', 'Future Batch Recommendation']
selected_columns = st.sidebar.multiselect("Columns to Display", options=all_columns, default=all_columns)

# ------------------------ Filter Data ------------------------
filtered_df = df[
    (df['region'].isin(selected_regions)) &
    (df['categories'].isin(selected_categories))
]

# ------------------------ Chart ------------------------
agg_df = (
    filtered_df.groupby(['region', 'itemcode'])
    .agg({'qty':'sum'})
    .reset_index()
)

top_items_df = (
    agg_df.sort_values(['region', 'qty'], ascending=[True, False])
    .groupby('region')
    .head(top_n)
)

fig = px.bar(
    top_items_df,
    y='region',
    x='qty',
    color='itemcode',
    text='qty',
    title=f"Top {top_n} Sold Itemcodes per Region",
    labels={'qty':'Total Quantity Sold', 'region':'Region', 'itemcode':'Item Code'},
    orientation='h'
)

fig.update_traces(textposition='outside')
fig.update_layout(barmode='group', yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig, use_container_width=True)

# ------------------------ Table ------------------------
# Aggregate table data
table_df = (
    filtered_df.groupby('itemcode')
    .agg({'qty':'sum', 'value':'sum'})
    .reset_index()
)

# Add serial number
table_df.insert(0, 'No', range(1, len(table_df)+1))

# Add forecast and batch recommendation
table_df['Next Month Forecast (Qty)'] = table_df['qty'] * 1.1
table_df['Future Batch Recommendation'] = table_df['Next Month Forecast (Qty)'].apply(lambda x: round(x / 10) * 10)

# Rename columns
table_df = table_df.rename(columns={
    'itemcode': 'Itemcode',
    'qty': 'Total Sold (Qty)',
    'value': 'Total Value (Rs)'
})

# Select only the columns user chose
table_df = table_df[selected_columns]

st.subheader("Itemcode Summary Table")
st.dataframe(table_df)
