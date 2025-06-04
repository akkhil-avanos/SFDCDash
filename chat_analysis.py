from openai import OpenAI
import streamlit as st

def get_openai_response(question, df):
    """Get OpenAI's analysis of the data based on user question"""
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
        
        df_info = df.describe().to_string()
        df_sample = df.head().to_string()
        
        prompt = f"""Given this data about GRPRO2.1 cases:
        Data Summary:
        {df_info}
        
        Sample Data:
        {df_sample}
        
        Question: {question}
        
        Please analyze the data and answer the question."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error getting analysis: {str(e)}"
