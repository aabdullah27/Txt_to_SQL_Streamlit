import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import os
import json
import re

# Load environment variables from .env file
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
model = "gemini-2.5-pro-exp-03-25"

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
            model=Gemini(id=model, api_key=google_api_key),
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
            model=Gemini(id=model, api_key=google_api_key),
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
            model=Gemini(id=model, api_key=google_api_key),
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

# Create a class for the Results Previewer Agent
class ResultsPreviewerAgent:
    def __init__(self):
        self.agent = Agent(
            model=Gemini(id=model, api_key=google_api_key),
            description="You are a database query execution specialist who can accurately predict the results of SQL queries when run against a given schema. You understand data relationships and can generate realistic sample data.",
            markdown=True
        )
    
    def preview_results(self, schema_analysis: str, user_query: str, sql_query: str) -> Dict[str, Any]:
        prompt = f"""
        Given the following database schema analysis:
        
        {schema_analysis}
        
        And this SQL query that was generated from the user's request:
        
        User's request: "{user_query}"
        
        SQL query:
        ```sql
        {sql_query}
        ```
        
        Please predict what results would be returned if this query was executed against a database with this schema.
        Generate a realistic sample dataset that would be returned.

        Respond in this exact JSON format:
        {{
            "columns": ["column1", "column2", ...],
            "data": [
                ["row1col1", "row1col2", ...],
                ["row2col1", "row2col2", ...],
                ...
            ],
            "row_count": number_of_rows,
            "matches_user_intent": true/false,
            "explanation": "Explanation of why these results match or don't match the user's intent",
            "suggested_improved_query": "Improved SQL query if the current one doesn't match user intent"
        }}
        
        For the data, generate realistic but fictitious sample data that would likely appear in this kind of database.
        Limit to a reasonable number of sample rows (5-10).
        
        Return ONLY the JSON without any additional text.
        """
        response = self.agent.run(prompt)
        
        # Clean the response to extract just the JSON
        content = response.content
        
        # Extract JSON from the response if needed
        json_match = re.search(r'{.*}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "columns": ["Error"],
                "data": [["Failed to parse results preview"]],
                "row_count": 1,
                "matches_user_intent": False,
                "explanation": "The results previewer failed to produce a proper response. Please review the SQL manually.",
                "suggested_improved_query": sql_query
            }

# Function to iteratively improve SQL query until it matches user intent
def refine_sql_until_correct(schema_analysis: str, user_query: str, initial_sql: str) -> Dict[str, Any]:
    max_iterations = 3
    current_sql = initial_sql
    iteration_history = []
    
    for i in range(max_iterations):
        # Get results preview
        previewer = ResultsPreviewerAgent()
        preview_results = previewer.preview_results(schema_analysis, user_query, current_sql)
        
        # Store this iteration
        iteration_history.append({
            "iteration": i + 1,
            "sql": current_sql,
            "results": preview_results
        })
        
        if preview_results["matches_user_intent"]:
            return {
                "sql": current_sql,
                "results": preview_results,
                "iterations": i + 1,
                "final": True,
                "history": iteration_history
            }
        
        # If there's a suggested improvement, use it
        if "suggested_improved_query" in preview_results and preview_results["suggested_improved_query"]:
            current_sql = preview_results["suggested_improved_query"]
        else:
            # If no suggestion, try again with the generator
            generator = SQLGeneratorAgent()
            feedback = f"Previous query didn't match user intent. Issues: {preview_results['explanation']}"
            prompt = f"""
            Based on the following database schema analysis:
            
            {schema_analysis}
            
            Convert this natural language query into a proper SQL command:
            
            "{user_query}"
            
            Previous attempt:
            ```sql
            {current_sql}
            ```
            
            Feedback on previous attempt:
            {feedback}
            
            Provide only the improved SQL command without any explanation.
            """
            current_sql = generator.agent.run(prompt).content
        
        # Validate the new SQL
        validator = SQLValidatorAgent()
        validation_result = validator.validate_sql(schema_analysis, user_query, current_sql)
        
        if not validation_result["is_valid"]:
            current_sql = validation_result["suggested_fix"]
    
    # If we reached max iterations, return the last attempt
    previewer = ResultsPreviewerAgent()
    final_preview = previewer.preview_results(schema_analysis, user_query, current_sql)
    
    # Add last iteration to history
    iteration_history.append({
        "iteration": max_iterations,
        "sql": current_sql,
        "results": final_preview
    })
    
    return {
        "sql": current_sql,
        "results": final_preview,
        "iterations": max_iterations,
        "final": False,
        "history": iteration_history
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
            # Container for displaying progress
            progress_container = st.empty()
            
            # Step 1: Generate SQL
            progress_container.info("Step 1/3: Generating initial SQL query...")
            generator = SQLGeneratorAgent()
            generated_sql = generator.generate_sql(st.session_state.schema_analysis, user_query)
            
            # Display initial SQL
            st.subheader("Generated SQL")
            st.code(generated_sql, language="sql")
            
            # Step 2: Validate SQL
            progress_container.info("Step 2/3: Validating SQL query...")
            validator = SQLValidatorAgent()
            validation_result = validator.validate_sql(st.session_state.schema_analysis, user_query, generated_sql)
            
            # Display validation results
            st.subheader("Validation Results")
            if validation_result["is_valid"]:
                st.success("✅ SQL query is valid!")
                st.markdown(validation_result["explanation"])
                valid_sql = generated_sql
            else:
                st.error("❌ SQL query has issues:")
                for issue in validation_result["issues"]:
                    st.markdown(f"- {issue}")
                
                st.markdown("**Suggested Fix:**")
                st.code(validation_result["suggested_fix"], language="sql")
                st.markdown(validation_result["explanation"])
                valid_sql = validation_result["suggested_fix"]
            
            # Step 3: Generate expected results (always do this step)
            progress_container.info("Step 3/3: Generating expected query results...")
            
            # First try with the direct results preview
            previewer = ResultsPreviewerAgent()
            initial_preview = previewer.preview_results(
                st.session_state.schema_analysis,
                user_query,
                valid_sql
            )
            
            # Display expected results header
            st.subheader("Expected Query Results")
            
            # If initial preview doesn't match user intent, refine it
            if not initial_preview["matches_user_intent"]:
                with st.spinner("Refining query to better match your intent..."):
                    refinement_result = refine_sql_until_correct(
                        st.session_state.schema_analysis,
                        user_query,
                        valid_sql
                    )
                
                if refinement_result["iterations"] > 1:
                    st.info(f"Query was refined {refinement_result['iterations']} times to better match your intent.")
                
                if refinement_result["sql"] != valid_sql:
                    st.markdown("**Optimized SQL Query:**")
                    st.code(refinement_result["sql"], language="sql")
                
                # Use the results from refinement
                results = refinement_result["results"]
            else:
                # Use the initial preview results
                results = initial_preview
            
            # Create a pandas DataFrame from the results
            df = pd.DataFrame(results["data"], columns=results["columns"])
            
            # Format the DataFrame for display
            st.dataframe(df)
            
            # Show explanation about the results
            with st.expander("Results Explanation", expanded=True):
                st.markdown(f"**Row Count:** {results['row_count']}")
                st.markdown(f"**Matches User Intent:** {'✅ Yes' if results['matches_user_intent'] else '❌ No'}")
                st.markdown(f"**Explanation:** {results['explanation']}")
            
            # Clear the progress indicator
            progress_container.empty()
            
            # Add to history
            st.session_state.query_history.append({
                "user_query": user_query,
                "sql": valid_sql if results == initial_preview else refinement_result["sql"],
                "results": results,
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
            
            # Display saved results
            st.markdown("**Results Preview:**")
            if 'results' in query and 'data' in query['results'] and 'columns' in query['results']:
                df = pd.DataFrame(query['results']["data"], columns=query['results']["columns"])
                st.dataframe(df)
            else:
                st.warning("No results preview available for this query.")