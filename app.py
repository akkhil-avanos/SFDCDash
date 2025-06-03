import io
import streamlit as st
import pandas as pd
from analyze_vscodetest import clean_and_enrich

st.title("Case Reason Categorizer")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df = clean_and_enrich(df)

    st.write("Preview of processed data:")
    st.dataframe(df.head())

    # --- Visuals Section ---

    # Bar chart of frequency of Concise Reasons
    st.subheader("Frequency of Concise Reasons")
    reason_counts = df['Concise Reason'].value_counts()
    reason_counts_df = reason_counts.reset_index()
    reason_counts_df.columns = ['Concise Reason', 'Count']
    reason_counts_df['Concise Reason'] = pd.Categorical(
        reason_counts_df['Concise Reason'],
        categories=reason_counts_df['Concise Reason'],
        ordered=True
    )
    reason_counts_df = reason_counts_df.sort_values('Count', ascending=False)
    st.bar_chart(
        data=reason_counts_df.set_index('Concise Reason')
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