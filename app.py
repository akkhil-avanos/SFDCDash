import io
import streamlit as st
import pandas as pd
from analyze_vscodetest import clean_and_enrich

# Set the page layout to wide
st.set_page_config(layout="wide")

st.title("SFDC Data Visualization Tool")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df = clean_and_enrich(df)

    st.write("Preview of processed data:")
    st.dataframe(df.head())

    # --- Visuals Section ---

    # Bar chart of frequency of individual Concise Reasons
    st.subheader("Frequency of Individual Reasons")
    all_reasons = df['Concise Reason'].str.split(',').explode().str.strip()
    reason_counts = all_reasons.value_counts()

    # Convert to DataFrame and set categorical index to preserve order
    reason_counts_df = reason_counts.reset_index()
    reason_counts_df.columns = ['Reason', 'Count']
    reason_counts_df['Reason'] = pd.Categorical(
        reason_counts_df['Reason'],
        categories=reason_counts_df['Reason'],
        ordered=True
    )
    reason_counts_df = reason_counts_df.sort_values('Count', ascending=False)

    st.bar_chart(reason_counts_df.set_index('Reason'))
   

    

    # --- Survival Curve Section ---
    st.subheader("Empirical Survival Curve: Time To Failure (TTF)")

    # Prepare survival data
    ttf = df['TTF'].dropna().sort_values()
    survival_prob = 1 - (ttf.rank(method="first") / len(ttf))

    survival_df = pd.DataFrame({
        "TTF": ttf.values,
        "Survival Probability": survival_prob.values
    })

    st.line_chart(
        data=survival_df.set_index("TTF")
    )

    # Widgets for average repair price and average TTF
    avg_repair_price = df['Repair Price (converted)'].mean()
    avg_ttf = df['TTF'].mean()

    col1, col2 = st.columns(2)
    col1.metric("Average Repair Price", f"${avg_repair_price:,.2f}")
    col2.metric("Average TTF (days)", f"{avg_ttf:.1f}")

    # --- Download Section ---
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    st.download_button(
        label="Download Excel with Reasons",
        data=output,
        file_name="output_with_reasons.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
