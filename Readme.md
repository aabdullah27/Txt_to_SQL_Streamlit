# 🔍 SQL Query Generator

Convert natural language into SQL queries with our powerful AI-powered tool.

**Live Demo:** [https://txt-to-sql-app.streamlit.app/](https://txt-to-sql-app.streamlit.app/)

## Overview

SQL Query Generator is a Streamlit application that transforms plain English queries into optimized SQL commands based on your database schema. Powered by LLama 3.3 70B (via Groq), this tool helps database users, analysts, and developers quickly generate accurate SQL without needing to remember exact syntax or table relationships.

## Features

- **Natural Language to SQL**: Describe what you want to query in plain English
- **Schema Analysis**: Upload or paste your database schema for accurate query generation
- **Query Validation**: Automatically validates generated SQL against your schema
- **Results Preview**: Shows expected query results with sample data
- **Query Refinement**: Iteratively improves queries to better match your intent
- **Query History**: Maintains a record of your previous queries for reference

## How It Works

The application uses a multi-agent system with specialized AI agents:

1. **Schema Analyzer**: Understands your database structure, tables, and relationships
2. **SQL Generator**: Converts natural language to SQL commands
3. **SQL Validator**: Ensures queries are correct and follow best practices
4. **Results Previewer**: Shows expected results with realistic sample data

## Getting Started

### Using the Web App

1. Visit [https://txt-to-sql-app.streamlit.app/](https://txt-to-sql-app.streamlit.app/)
2. Input your database schema (paste or upload)
3. Click "Analyze Schema"
4. Enter your query in plain English
5. Click "Generate SQL"
6. Review and use the generated SQL

### Running Locally

1. Clone the repository
2. Install dependencies:
   ```
   pip install streamlit pandas agno dotenv
   ```
3. Create a `.env` file with your Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   ```
4. Run the application:
   ```
   streamlit run app.py
   ```

## Example Usage

1. **Input Schema**:
   ```sql
   CREATE TABLE customers (
     customer_id INT PRIMARY KEY,
     name VARCHAR(100),
     email VARCHAR(100),
     join_date DATE
   );
   
   CREATE TABLE orders (
     order_id INT PRIMARY KEY,
     customer_id INT,
     order_date DATE,
     total_amount DECIMAL(10,2),
     FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
   );
   ```

2. **Natural Language Query**:
   "Show me all customers who spent more than $500 in total, along with their total order amount"

3. **Generated SQL**:
   ```sql
   SELECT c.customer_id, c.name, c.email, SUM(o.total_amount) as total_spent
   FROM customers c
   JOIN orders o ON c.customer_id = o.customer_id
   GROUP BY c.customer_id, c.name, c.email
   HAVING SUM(o.total_amount) > 500
   ORDER BY total_spent DESC;
   ```

## Requirements

- Streamlit
- Pandas
- Agno Agents
- Groq API access
- Python 3.10+

## Limitations

- Currently supports standard SQL syntax
- Generated queries may need adjustment for specific database dialects (MySQL, PostgreSQL, etc.)
- Complex queries or specialized database features may require manual refinement

## Feedback and Contributions

We welcome contributions and feedback to improve this tool. Please feel free to submit issues or pull requests.
