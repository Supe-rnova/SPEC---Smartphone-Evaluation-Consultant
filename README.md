SPEC — Smartphone Evaluation Consultant
SPEC (Smartphone Evaluation Consultant) is an AI-powered smartphone recommendation agent that helps users discover the most suitable smartphone based on their budget, preferences, and desired specifications through natural language conversation.
Instead of manually filtering products or comparing specifications across dozens of devices, users simply describe what they are looking for, and SPEC handles the rest.

Live Demo

Try SPEC here:
https://spec-smartphone-evaluation-consultant.onrender.com


Problem Statement
Finding the right smartphone often requires:
Comparing hundreds of models
Understanding technical specifications
Filtering devices across multiple constraints
Balancing performance, price, battery life, camera quality, and other features
SPEC simplifies this process by acting as an intelligent smartphone consultant capable of understanding user requirements in plain language.

Features
Natural Language Search
Users can describe requirements conversationally:
"I need a gaming phone under $700 with 12GB RAM and 5G support."
"Show me a lightweight Samsung phone with a good camera."
"I want the best photography phone under $1000."

Multi-Turn Conversations
SPEC remembers previous requirements and allows users to refine their search naturally.
Example:
User:
I need a gaming phone under $800.
User:
Make it Samsung only.
The agent updates only the relevant criteria while preserving previous constraints.

Intelligent Smartphone Filtering
The system supports filtering by:
Budget
Brand
RAM
Storage
Battery Capacity
Camera Resolution
Refresh Rate
Fast Charging
Operating System
5G Support
NFC
Wireless Charging
Water Resistance
Weight
Color
Usage Type (Gaming, Photography, Productivity, Everyday Use)

AI-Powered Recommendations
After identifying matching devices, SPEC:
Selects the best candidates
Compares the top smartphones
Generates concise explanations
Provides a final recommendation with reasoning

How It Works
User Query
    │
    ▼
Gemini LLM
(Requirement Extraction)
    │
    ▼
Structured Search Criteria
    │
    ▼
Smartphone Dataset
    │
    ▼
Filtering Engine
    │
    ▼
Matching Devices
    │
    ▼
Gemini LLM
(Ranking & Recommendation)
    │
    ▼
Final Recommendation


Technology Stack
Backend
Python
Flask
AI Layer
Google Gemini 2.5 Flash Lite
Data Processing
Pandas
Deployment
Render
Version Control
GitHub

Project Structure
SPEC/
│
├── app.py
├── agent.py
├── phones.csv
├── requirements.txt
├── test_gemini.py
├── README.md
└── .gitignore


Example Queries
Gaming
Find me a gaming phone under $700 with 12GB RAM and 5G.
Photography
Show me the best camera phone under $1000.
Productivity
I need a lightweight Android phone with excellent battery life.
Budget
Recommend the best phone under $400.


