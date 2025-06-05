import io
import streamlit as st
import pandas as pd
import altair as alt
import os
from analyze_vscodetest import clean_and_enrich, filter_by_product_type, get_first_failure_survival_data
from auth import check_password
import openai
from chat_analysis import get_openai_response

# Show content only if password is correct
if check_password():
    # Set the page layout to wide
    st.set_page_config(layout="wide")

    st.title("SFDC GRPRO2.1 Data Visualization Tool")

    # Default data file path
    default_file = "SFDC GRPro2.1 datadump.xlsx"

    # Load default data if it exists
    try:
        df = pd.read_excel(default_file)
        st.success(f"Loaded default dataset: {default_file}")
    except FileNotFoundError:
        st.warning(f"Default dataset not found: {default_file}")
        df = None

    # Option to upload different data
    st.sidebar.subheader("Data Source")
    use_different_data = st.sidebar.checkbox("Use different dataset")

    if use_different_data:
        uploaded_file = st.sidebar.file_uploader("Upload your Excel file", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.success("Successfully loaded uploaded dataset")





    #-----Filters---------

    if df is not None:
        total_cases = len(df)  # Get total before filtering
        df = clean_and_enrich(df)
        
        # Sidebar Filters Section
        st.sidebar.subheader("Filters")
        
        # 1. Product Type Filter
        filter_option = st.sidebar.selectbox(
            "Choose Product Type to analyze:",
            ("All", "Rental", "Non-Rental")
        )
        df = filter_by_product_type(df, filter_option)

        # 2. Warranty Type Filter
        warranty_types = ["All"] + sorted(df['Warranty type'].unique().tolist())
        warranty_filter = st.sidebar.selectbox(
            "Choose Warranty Type to analyze:",
            warranty_types
        )
        
        if warranty_filter != "All":
            df = df[df['Warranty type'] == warranty_filter]

        # 3. Manufacturing Year Range Filter
        min_year = int(df['Manufacture Year'].min())
        max_year = int(df['Manufacture Year'].max())
        
        year_range = st.sidebar.slider(
            "Select Manufacturing Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year)
        )
        
        # 4. Case Opened Year Range Filter
        min_opened_year = int(pd.to_datetime(df['Opened Date']).dt.year.min())
        max_opened_year = int(pd.to_datetime(df['Opened Date']).dt.year.max())
        
        opened_year_range = st.sidebar.slider(
            "Select Case Opened Year Range",
            min_value=min_opened_year,
            max_value=max_opened_year,
            value=(min_opened_year, max_opened_year)
        )
        
        # Apply both year filters
        df = df[
            (df['Manufacture Year'] >= year_range[0]) & 
            (df['Manufacture Year'] <= year_range[1]) &
            (pd.to_datetime(df['Opened Date']).dt.year >= opened_year_range[0]) &
            (pd.to_datetime(df['Opened Date']).dt.year <= opened_year_range[1])
        ]

        # Display case counts
        filtered_cases = len(df)
        col1, col2 = st.columns(2)
        col1.metric("Total Cases", f"{total_cases:,}")
        col2.metric("Filtered Cases", f"{filtered_cases:,}")

        # Preview
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
       

        


        # --- Histogram of Concise Reason Frequency by Time ---

        st.subheader("Concise Reason Frequency by Time")

        # Get unique reasons for dropdown
        unique_reasons = sorted(df['Concise Reason'].str.split(',').explode().str.strip().unique())
        selected_reason = st.selectbox(
            "Select Reason to analyze:",
            unique_reasons
        )

        # Add toggle for year/month view
        time_granularity = st.selectbox(
            "Select time granularity",
            ("Month", "Year"),
            key="reason_time_granularity"  # unique key to avoid conflict
        )

        # Filter for selected reason
        reason_mask = df['Concise Reason'].str.contains(selected_reason, na=False)
        reason_df = df[reason_mask].copy()

        if time_granularity == "Month":
            # Monthly view
            reason_df['Month'] = pd.to_datetime(reason_df['Opened Date']).dt.strftime('%Y-%m')
            month_reason_counts = reason_df.groupby('Month').size().sort_index()
            
            st.bar_chart(month_reason_counts)

        else:
            # Yearly view
            year_reason_counts = reason_df.groupby(
                pd.to_datetime(reason_df['Opened Date']).dt.year
            ).size().sort_index()
            
            st.bar_chart(year_reason_counts)
            
        






        # --- Survival Curve Section ---

        st.subheader("First Failure Survival Curve")
        
        # Get survival data using only first failures
        survival_df = get_first_failure_survival_data(df)

        st.line_chart(
            data=survival_df.set_index("Years")
        )

        # Add explanation
        st.caption(
            "Given that a product has failed, this curve shows the probability that the product is at least this old (in years)"
        )

        # --- Time Until First Failure Section ---
        st.subheader("Time Until First Failure Analysis")

        # Group by Asset/Serial No and get first failure for each
        first_failures = df.groupby('Asset/Serial No').agg({
            'TTF': 'first',  # Get first TTF for each asset
            'Manufacture Date': 'first'  # Get manufacture date
        }).reset_index()

        # Convert TTF to years for consistency with survival curve
        first_failures['TTF_Years'] = first_failures['TTF'].dropna() / 365

        # Create histogram of first failures
        st.write("Distribution of Time Until First Failure (Years)")
        
        # Create bins for the histogram
        max_ttf = first_failures['TTF_Years'].max()
        bin_size = 0.5  # 6-month bins
        bins = range(0, int(max_ttf) + 2, 1)  # +2 to ensure last bin is included
        
        # Calculate histogram data
        hist_data = pd.cut(first_failures['TTF_Years'], 
                          bins=bins, 
                          labels=[f"{i}-{i+1}" for i in range(len(bins)-1)])
        hist_counts = hist_data.value_counts().sort_index()
        
        # Plot histogram
        st.bar_chart(hist_counts)

        # Calculate time between failures
        def get_time_between_failures(group):
            # Sort by TTF
            sorted_ttf = sorted(group['TTF'].dropna())
            # Calculate differences between consecutive failures
            return [sorted_ttf[i+1] - sorted_ttf[i] for i in range(len(sorted_ttf)-1)]

        # Get time between failures for assets with multiple failures
        time_between_failures = []
        for name, group in df.groupby('Asset/Serial No'):
            if len(group) > 1:  # Only consider assets with multiple failures
                time_between_failures.extend(get_time_between_failures(group))

        # Convert to years for consistency
        time_between_failures_years = [t/365 for t in time_between_failures]
        avg_time_between_failures = sum(time_between_failures_years)/len(time_between_failures_years) if time_between_failures_years else 0

        # Update columns to include new metric
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Median Time to First Failure (Years)", 
                   f"{first_failures['TTF_Years'].median():.1f}")
        col2.metric("Average Time to First Failure (Years)", 
                   f"{first_failures['TTF_Years'].mean():.1f}")
        col3.metric("Number of First Failures", 
                   f"{len(first_failures.dropna())}")
        col4.metric("Average Time Between Failures (Years)", 
                   f"{avg_time_between_failures:.1f}")






        # --- Histogram of Failures by Manufacturing Year ---

        st.subheader("Failure Frequency by Manufacturing Date")

        # Add toggle for year/month view
        date_granularity = st.selectbox(
            "Select view",
            ("Year", "Month")
        )

        if date_granularity == "Year":
            # Existing yearly view
            year_counts = df['Manufacture Year'].dropna().astype(int).value_counts().sort_index()
            st.bar_chart(year_counts)
        else:
            # Monthly view
            df['Manufacture Month'] = pd.to_datetime(df['Manufacture Date']).dt.strftime('%Y-%m')
            month_counts = df['Manufacture Month'].value_counts().sort_index()
            st.bar_chart(month_counts)





        # --- Histogram of Failure Frequency per Asset/Serial Number ---

        st.subheader("Failure Frequency per Asset/Serial Number")

        # Count failures per asset/serial number
        failure_counts = df['Asset/Serial No'].value_counts()

        # Make a DataFrame mapping Asset/Serial No to failure count
        failures_df = failure_counts.rename_axis('Asset/Serial No').reset_index(name='Failures')

        # Make a histogram: how many products failed 1, 2, 3... times
        hist_df = failures_df['Failures'].value_counts().sort_index().rename_axis('Failures').reset_index(name='Num Products')

        # Altair selection
        selection = alt.selection_single(fields=['Failures'], empty='none')

        # Altair chart (still interactive for highlight)
        bar = alt.Chart(hist_df).mark_bar().encode(
            x=alt.X('Failures:O', title='Number of Failures'),
            y=alt.Y('Num Products:Q', title='Number of Products'),
            color=alt.value('steelblue')
        )
        st.altair_chart(bar, use_container_width=True)

        selected_failures = st.selectbox(
            "Select number of failures to view associated Asset/Serial Numbers:",
            hist_df['Failures']
        )

        # Get all asset/serial numbers with the selected number of failures
        matching_assets = failures_df[failures_df['Failures'] == selected_failures]['Asset/Serial No']

        # Show only the final output, remove debug statements
        st.write(f"Asset/Serial Numbers for products with {selected_failures} failures:")
        st.write(matching_assets.tolist())






        # Widgets for average repair price and average TTF
        avg_ttf = df['TTF'].mean()

        col1, col2 = st.columns(2)
        if 'Repair Price (converted)' in df.columns:
            avg_repair_price = df['Repair Price (converted)'].mean()
            col1.metric("Average Repair Price", f"${avg_repair_price:,.2f}")
      







        # --- OpenAI Analysis Section ---
        if df is not None:
            st.subheader("Ask about the Data")
            user_question = st.text_input("What would you like to know about the data?")
            
            if user_question:
                if 'OPENAI_API_KEY' in st.secrets:
                    openai.api_key = st.secrets['OPENAI_API_KEY']
                    with st.spinner('Analyzing data...'):
                        response = get_openai_response(user_question, df)
                        st.write("Analysis:", response)
                else:
                    st.error("OpenAI API key not found in secrets")

            st.divider()  # Add visual separation






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

