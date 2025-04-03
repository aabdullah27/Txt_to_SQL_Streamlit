import streamlit as st
import pandas as pd
from typing import Dict, Any
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
groq_model = "llama-3.3-70b-versatile"

# Set page configuration
st.set_page_config(
    page_title="SQL Query Generator",
    page_icon="🔍",
    layout="wide"
)

# App title and description
st.title("🔍 SQL Query Generator")
st.markdown("""
This app converts natural language into SQL queries based on your database schema.
Upload your schema, describe your query in plain English, and get working SQL commands.
""")

# Initialize session state variables if they don't exist
if 'schema' not in st.session_state:
    st.session_state.schema = ""
if 'query_history' not in st.session_state:
    st.session_state.query_history = []

# Create a class for the Schema Analyzer Agent
class SchemaAnalyzerAgent:
    def __init__(self):
        self.agent = Agent(
            model=Groq(id=groq_model, api_key=groq_api_key),
            description="You are a database expert who analyzes and understands database schemas. Identify tables, columns, relationships, and data types accurately.",
            markdown=True
        )
    
    def analyze_schema(self, schema: str) -> str:
        prompt = f"""
        Analyze this database schema and provide a comprehensive understanding of it:
        
        {schema}
        
        Please identify:
        1. All tables and their purposes
        2. All columns in each table and their data types
        3. Primary keys and foreign keys
        4. Relationships between tables
        5. Any constraints or special considerations
        
        Format your response as a structured analysis that could be used by another agent to generate SQL queries.
        """
        response = self.agent.run(prompt)
        return response.content

# Create a class for the SQL Generator Agent
class SQLGeneratorAgent:
    def __init__(self):
        self.agent = Agent(
            model=Groq(id=groq_model, api_key=groq_api_key),
            description="You are an SQL expert who converts natural language queries into precise SQL commands based on database schemas.",
            markdown=True
        )
    
    def generate_sql(self, schema_analysis: str, user_query: str) -> str:
        prompt = f"""
        Based on the following database schema analysis:
        
        {schema_analysis}
        
        Convert this natural language query into a proper SQL command:
        
        "{user_query}"
        
        Provide only the SQL command without any explanation. Make sure the SQL follows best practices and is optimized.
        """
        response = self.agent.run(prompt)
        return response.content

# Create a class for the SQL Validator Agent
class SQLValidatorAgent:
    def __init__(self):
        self.agent = Agent(
            model=Groq(id=groq_model, api_key=groq_api_key),
            description="You are a meticulous SQL validator who ensures SQL commands are correct, efficient, and match the user's intent and the database schema.",
            markdown=True
        )
    
    def validate_sql(self, schema_analysis: str, user_query: str, generated_sql: str) -> Dict[str, Any]:
        prompt = f"""
        You need to validate if this SQL query correctly answers the user's request and is compatible with the database schema.
        
        Database Schema Analysis:
        {schema_analysis}
        
        User's Natural Language Query:
        "{user_query}"
        
        Generated SQL Query:
        ```sql
        {generated_sql}
        ```
        
        Please validate the SQL query and provide your assessment in this exact JSON format:
        {{
            "is_valid": true/false,
            "issues": ["issue1", "issue2", ...] (empty list if no issues),
            "suggested_fix": "fixed SQL query" (only if there are issues),
            "explanation": "brief explanation of issues or confirmation of validity"
        }}
        
        Return ONLY the JSON without any additional text.
        """
        response = self.agent.run(prompt)
        
        # Clean the response to extract just the JSON
        content = response.content
        import json
        import re
        
        # Extract JSON from the response if needed
        json_match = re.search(r'{.*}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "is_valid": False,
                "issues": ["Failed to parse validation response"],
                "suggested_fix": generated_sql,
                "explanation": "The validator failed to produce a proper response. Please review the SQL manually."
            }

# Create sidebar for schema input
with st.sidebar:
    st.header("Database Schema")
    schema_input_method = st.radio(
        "Choose how to input your schema:",
        ("Paste Schema", "Upload Schema File")
    )
    
    if schema_input_method == "Paste Schema":
        schema_text = st.text_area(
            "Paste your database schema here (SQL CREATE statements or description):",
            height=300,
            value=st.session_state.schema
        )
        if schema_text:
            st.session_state.schema = schema_text
    else:
        schema_file = st.file_uploader("Upload a schema file", type=['sql', 'txt'])
        if schema_file is not None:
            st.session_state.schema = schema_file.getvalue().decode("utf-8")
            st.text_area("Uploaded Schema:", st.session_state.schema, height=300, disabled=True)
    
    if st.button("Analyze Schema"):
        if st.session_state.schema:
            with st.spinner("Analyzing schema..."):
                analyzer = SchemaAnalyzerAgent()
                st.session_state.schema_analysis = analyzer.analyze_schema(st.session_state.schema)
                st.success("Schema analyzed successfully!")
        else:
            st.error("Please provide a database schema first.")

# Main area for query input and results
st.header("Generate SQL Query")

if 'schema_analysis' in st.session_state:
    with st.expander("Schema Analysis", expanded=False):
        st.markdown(st.session_state.schema_analysis)
    
    # User query input
    user_query = st.text_area("What would you like to query? (in plain English)", height=100)
    
    if st.button("Generate SQL"):
        if user_query:
            with st.spinner("Generating SQL..."):
                # Generate SQL
                generator = SQLGeneratorAgent()
                generated_sql = generator.generate_sql(st.session_state.schema_analysis, user_query)
                
                # Validate SQL
                validator = SQLValidatorAgent()
                validation_result = validator.validate_sql(st.session_state.schema_analysis, user_query, generated_sql)
                
                # Display results
                st.subheader("Generated SQL")
                st.code(generated_sql, language="sql")
                
                # Display validation results
                st.subheader("Validation Results")
                if validation_result["is_valid"]:
                    st.success("✅ SQL query is valid!")
                    st.markdown(validation_result["explanation"])
                    final_sql = generated_sql
                else:
                    st.error("❌ SQL query has issues:")
                    for issue in validation_result["issues"]:
                        st.markdown(f"- {issue}")
                    
                    st.subheader("Suggested Fix")
                    st.code(validation_result["suggested_fix"], language="sql")
                    st.markdown(validation_result["explanation"])
                    final_sql = validation_result["suggested_fix"]
                
                # Add to history
                st.session_state.query_history.append({
                    "user_query": user_query,
                    "sql": final_sql,
                    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        else:
            st.error("Please enter a query first.")
else:
    st.info("Please analyze your database schema first using the sidebar.")

# Query history section
if st.session_state.query_history:
    st.header("Query History")
    for i, query in enumerate(reversed(st.session_state.query_history)):
        with st.expander(f"{query['timestamp']} - {query['user_query'][:50]}..."):
            st.markdown(f"**Original Query:** {query['user_query']}")
            st.markdown("**Generated SQL:**")
            st.code(query['sql'], language="sql")

# Footer
st.markdown("---")
st.markdown("Built with Streamlit, Groq LLMs, and Agno Agents")