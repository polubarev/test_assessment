# AI/ML Engineer Coding Exercise - LLM-Powered Log Analysis

## Overview
Build a REST API service that can answer natural language questions about SSH log data using a local LLM (Ollama) with an open-source model. This exercise tests your ability to work with LLM integration, data processing, and scalable system design.

## Dataset
You'll work with a provided SSH log dataset containing authentication attempts, connections, and security events. The system should be designed to handle much larger log volumes than the provided sample. See `ssh-audit.log`.

## Requirements

### 1. Local LLM Setup
- Use Ollama with an open-source model (Llama 3.1, Mistral, CodeLlama, or similar)
- Set up the LLM client and implement prompt engineering for log analysis
- Handle model loading and response generation
- Ensure the LLM can provide accurate answers about the log data

### 2. Scalable Log Processing
- Parse the provided SSH logs efficiently
- Design a system that can handle significantly larger log volumes (10x, 100x more than the sample)
- Create an efficient data structure or indexing system for fast LLM queries
- Consider how to pre-process, index, or summarize logs for optimal LLM performance

### 3. Natural Language Query API
Create a REST API endpoint that accepts natural language questions:

```
POST /api/query
{
  "question": "What are the top 5 attacking IP addresses?"
}

POST /api/query  
{
  "question": "Show me all failed login attempts from yesterday"
}

POST /api/query
{
  "question": "Are there any signs of brute force attacks?"
}

POST /api/query
{
  "question": "Which usernames are being targeted most frequently?"
}
```

The API should return structured responses that answer the questions accurately based on the log data.

## Technical Constraints
- Use any programming language/framework you prefer
- You can use any copilot to help you (Cursor, GitHub Copilot, Claude, ChatGPT, etc.)
- Include basic error handling and input validation
- Focus on LLM integration, data processing efficiency, and system scalability
- The system should work with the provided dataset and be designed for larger volumes

## Deliverables
1. **Working API service** with natural language query capabilities
2. **Scalability documentation** explaining how your system handles larger datasets
3. **Brief README** including:
   - Setup instructions for Ollama and your chosen model
   - API documentation with example queries and responses
   - Your approach to log processing and LLM integration
   - Assumptions and limitations

## Time Limit
Complete this exercise within 2 hours.
