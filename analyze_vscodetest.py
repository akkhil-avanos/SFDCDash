import pandas as pd
from datetime import datetime, timedelta
from reason_keywords import reason_keywords
import os

def extract_manufacture_date(serial):
    try:
        code = serial[2:7]
        year = 2000 + int(code[:2])
        day_of_year = int(code[2:])
        return datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
    except:
        return pd.NaT

def format_reason(reason):
    # Remove any leading numbers, dashes, and whitespace
    return pd.Series(reason).str.replace(r'^[\s\-0-9]+', '', regex=True).str.strip().values[0]

def categorize_description_and_case(description, case_reason):
    reasons_found = set()
    desc_lower = str(description).lower()
    words = set(desc_lower.replace(",", " ").replace(".", " ").replace(";", " ").split())
    # Add the cleaned case reason
    if pd.notna(case_reason):
        reasons_found.add(format_reason(str(case_reason).strip()))
    for reason, keywords in reason_keywords.items():
        if reason == case_reason:
            continue
        for kw in keywords:
            if " " in kw:
                if kw in desc_lower:
                    reasons_found.add(format_reason(reason))
                    break
            else:
                if kw in words:
                    reasons_found.add(format_reason(reason))
                    break
    return ", ".join(sorted(reasons_found)) if reasons_found else "Other"

def clean_and_enrich(df):
    # Standardize Asset/Serial No
    df['Asset/Serial No'] = df['Asset/Serial No'].astype(str).str.strip()
    
    # Manufacture Date extraction
    df['Manufacture Date'] = df['Asset/Serial No'].apply(extract_manufacture_date)
    df['Opened Date'] = pd.to_datetime(df['Opened Date'])
    df['Manufacture Date'] = pd.to_datetime(df['Manufacture Date'])
    df['TTF'] = (df['Opened Date'] - df['Manufacture Date']).dt.days
    
    # Extract Manufacturing Year
    df['Manufacture Year'] = pd.to_datetime(df['Manufacture Date'], errors='coerce').dt.year

    # Clean the Case Reason column
    df['Case Reason'] = df['Case Reason'].str.replace(r'^.*?-\s*', '', regex=True)
    df['Case Reason'] = df['Case Reason'].str.replace(
        r'^Cosmetic/Physical Damage.*$', 'Cosmetic/Physical Damage', regex=True
    )

    # Concise Reason
    df['Concise Reason'] = df.apply(
        lambda row: categorize_description_and_case(row['Description'], row['Case Reason']),
        axis=1
    )
    return df

def categorize_with_openai(description, case_reason, reason_keywords):
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # or use your key directly

    prompt = (
        "Given the following case description and a list of possible reasons, "
        "return all reasons (comma-separated, no duplicates) that apply to the description. "
        "Only use reasons from the list. "
        f"Description: \"{description}\"\n"
        f"Possible reasons: {', '.join(reason_keywords.keys())}\n"
        f"Case Reason: \"{case_reason if pd.notna(case_reason) else ''}\"\n"
        "Output:"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0
    )
    concise_reasons = response.choices[0].message.content.strip()
    unique_reasons = list(dict.fromkeys([r.strip() for r in concise_reasons.split(",") if r.strip()]))
    return ", ".join(unique_reasons)

def filter_by_product_type(df, filter_option):
    """
    Filter DataFrame based on product type (Rental vs Non-Rental)
    """
    if filter_option == "Rental":
        return df[df['Product Code'].astype(str).str.contains("RN", case=False, na=False)]
    elif filter_option == "Non-Rental":
        return df[~df['Product Code'].astype(str).str.contains("RN", case=False, na=False)]
    return df

def get_first_failure_survival_data(df):
    """Calculate survival curve data using only first failures"""
    # Group by Asset/Serial No and get first failure for each
    first_failures = df.groupby('Asset/Serial No').agg({
        'TTF': 'first'  # Get first TTF for each asset
    }).reset_index()
    
    # Convert to years and prepare survival data
    ttf_years = first_failures['TTF'].dropna().sort_values() / 365
   # survival_prob = 1 - (ttf_years.rank(method="first") / len(ttf_years))
    survival_prob =  (ttf_years.rank(method="first") / len(ttf_years))
    return pd.DataFrame({
        "Years": ttf_years.values,
        "Probability": survival_prob.values
    })



