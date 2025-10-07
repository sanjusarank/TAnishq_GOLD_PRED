import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Jewelry Demand Dashboard", layout="wide")

# ------------------------ Load Data ------------------------
df = pd.read_csv("final1.csv")

# Convert docdate to datetime and drop invalid dates
df["docdate"] = pd.to_datetime(df["docdate"], errors="coerce")
df = df.dropna(subset=["docdate"])

# Convert qty and value to numeric safely and drop invalid rows
df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")
df = df.dropna(subset=["qty", "value"])

# Ensure categories are strings
df["categories"] = df["categories"].astype(str)

# ------------------------ Sidebar Filters ------------------------
st.sidebar.header("Filters")

regions = sorted(df["region"].dropna().unique())
selected_region = st.sidebar.selectbox("Select Region", regions)

categories = sorted(df["categories"].dropna().unique())
selected_categories = st.sidebar.multiselect("Select Category(s)", categories, default=categories)

top_n_items = st.sidebar.slider("Number of top itemcodes to show", min_value=1, max_value=10, value=5)
top_n_btq = st.sidebar.slider("Number of top BTQs to show in chart", min_value=3, max_value=10, value=5)

# ------------------------ Filter Data by Region & Category ------------------------
filtered_df = df[
    (df["region"] == selected_region) &
    (df["categories"].isin(selected_categories))
]

if filtered_df.empty:
    st.warning("No data available for selected region and category combination.")
else:
    # ------------------------ Top Itemcodes per Region Chart ------------------------
    agg_df = (
        filtered_df.groupby(['region', 'itemcode'])
        .agg({'qty':'sum'})
        .reset_index()
    )

    top_items_df = (
        agg_df.sort_values(['region', 'qty'], ascending=[True, False])
        .groupby('region')
        .head(top_n_items)
    )

    fig = px.bar(
        top_items_df,
        y='region',
        x='qty',
        color='itemcode',
        text='qty',
        title=f"Top {top_n_items} Sold Itemcodes in {selected_region}",
        labels={'qty':'Total Quantity Sold', 'region':'Region', 'itemcode':'Item Code'},
        orientation='h'
    )

    fig.update_traces(textposition='outside')
    fig.update_layout(barmode='group', yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

    # ------------------------ Identify Top N Itemcodes ------------------------
    item_summary = filtered_df.groupby("itemcode")["qty"].sum().reset_index()
    top_items = item_summary.sort_values("qty", ascending=False).head(top_n_items)

    st.title(f"💎 Top {top_n_items} Itemcodes in Region {selected_region} (Filtered by Category)")

    description_text = ""
    all_table_data = []

    # ------------------------ Loop Through Top Itemcodes ------------------------
    for idx, row in top_items.iterrows():
        item = row["itemcode"]
        total_sold = row["qty"]

        # Analyze BTQs
        item_df = filtered_df[filtered_df["itemcode"] == item]
        btq_summary = item_df.groupby("BTQ")["qty"].sum().reset_index().sort_values("qty", ascending=False)

        mean_sales = btq_summary["qty"].mean()
        std_sales = btq_summary["qty"].std()
        consistency_score = round((1 - (std_sales / mean_sales)) * 100, 2) if mean_sales > 0 else 0

        # Identify weak BTQs (<60% of mean)
        threshold = mean_sales * 0.6
        weak_btqs = btq_summary[btq_summary["qty"] < threshold]["BTQ"].tolist()
        strong_btqs = btq_summary[btq_summary["qty"] >= threshold]["BTQ"].tolist()

        # Trend / forecast (simple last 2 months)
        monthly_sales = item_df.groupby(pd.Grouper(key="docdate", freq="M"))["qty"].sum().reset_index()
        if len(monthly_sales) >= 2:
            last_2 = monthly_sales.tail(2)["qty"].values
            trend = last_2[-1] - last_2[-2]
        else:
            trend = 0

        if trend > 0:
            trend_text = "📈 Sales are increasing — consider producing more for high-performing BTQs."
        elif trend < 0:
            trend_text = "📉 Sales are decreasing — reduce production for underperforming BTQs."
        else:
            trend_text = "➖ Sales stable — maintain current stock levels."

        # ------------------------ Display Summary ------------------------
        st.subheader(f"Itemcode: {item} | Total Sold: {total_sold}")

        st.markdown(f"""
        **Category:** {item_df['categories'].iloc[0]}  
        **Mean Sales Across BTQs:** {mean_sales:.2f}  
        **Standard Deviation Across BTQs:** {std_sales:.2f}  
        **Consistency Score:** {consistency_score}%  
        """)

        if weak_btqs:
            st.warning(f"This item is performing **poorly in {len(weak_btqs)} BTQs**: {', '.join(weak_btqs)}")
        else:
            st.success("This item is performing well across all BTQs.")

        st.info(trend_text)

        # ------------------------ Horizontal Bar Chart ------------------------
        fig = px.bar(
            btq_summary.head(top_n_btq),
            x="qty",
            y="BTQ",
            orientation="h",
            text="qty",
            title=f"Top {top_n_btq} BTQs for Itemcode {item}",
            labels={"qty":"Total Sold","BTQ":"Boutique"}
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        # ------------------------ Prepare Table Data ------------------------
        table_data = {
            "Itemcode": item,
            "Category": item_df['categories'].iloc[0],
            "Total Sold (Qty)": total_sold,
            "Total Value (Rs)": item_df['value'].sum(),
            "Next Month Forecast (Qty)": total_sold * 1.1,
            "Future Batch Recommendation": round((total_sold * 1.1) / 10) * 10
        }
        all_table_data.append(table_data)

        # ------------------------ Description ------------------------
        description_text += f"✅ **Itemcode {item}** in category **{item_df['categories'].iloc[0]}** is performing well in region **{selected_region}**, strong in BTQs: {', '.join(str(b) for b in strong_btqs)}. "

        if weak_btqs:
            description_text += f"However, weaker performance in BTQs: {', '.join(str(b) for b in weak_btqs)}. "

        if trend > 0:
            description_text += "Sales are trending upwards — consider producing more.\n\n"
        elif trend < 0:
            description_text += "Sales are trending downwards — reduce extra production.\n\n"
        else:
            description_text += "Sales are stable — maintain current stock levels.\n\n"

    # ------------------------ Display Description ------------------------
    st.subheader("📄 Analysis Summary")
    st.markdown(description_text)

    # ------------------------ Display Table ------------------------
    st.subheader("Itemcode Summary Table")
    table_df = pd.DataFrame(all_table_data)
    table_df = table_df[[
        "Itemcode", "Category", "Total Sold (Qty)", "Total Value (Rs)", 
        "Next Month Forecast (Qty)", "Future Batch Recommendation"
    ]]
    table_df.insert(0, 'No', range(1, len(table_df)+1))
    st.dataframe(table_df)
