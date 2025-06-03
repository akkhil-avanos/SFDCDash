import pandas as pd
from datetime import datetime, timedelta
from reason_keywords import reason_keywords
#import openai
import os
#openai.api_key = "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"

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
    # Manufacture Date extraction
    df['Manufacture Date'] = df['Asset/Serial No'].apply(extract_manufacture_date)
    df['Opened Date'] = pd.to_datetime(df['Opened Date'])
    df['Manufacture Date'] = pd.to_datetime(df['Manufacture Date'])
    df['TTF'] = (df['Opened Date'] - df['Manufacture Date']).dt.days

    # Clean the Case Reason column to remove any prefix like "GRPRO", numbers, and dashes
    df['Case Reason'] = df['Case Reason'].str.replace(r'^.*?-\s*', '', regex=True)

    # Concise Reason
    df['Concise Reason'] = df.apply(
       lambda row: categorize_description_and_case(row['Description'], row['Case Reason']),
       # lambda row: categorize_with_openai(row['Description'], row['Case Reason'], reason_keywords), 
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

# df = pd.read_excel('vscodetest2.xlsx')
# df = clean_and_enrich(df)
# df.to_excel('vscodetest2_with_reasons.xlsx', index=False)



