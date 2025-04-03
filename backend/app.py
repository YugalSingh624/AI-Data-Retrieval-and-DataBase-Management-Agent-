from flask import Flask, request, jsonify, render_template, Response
from dotenv import load_dotenv
from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.googlesearch import GoogleSearch
from phi.tools.baidusearch import BaiduSearch
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.storage.agent.sqlite import SqlAgentStorage
from datetime import datetime
import re
import os
import json
from flask_cors import CORS
from bson import ObjectId
from pymongo import MongoClient

# It's a point do not CTRL Z after this

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {
    "origins": ["https://ai-powered-search-assistant-eight.vercel.app"],
    "methods": ["GET", "POST", "OPTIONS", "DELETE", "PUT"],
    "allow_headers": ["Content-Type", "Authorization"]
}})  # This will enable CORS for all routes

# Get current date information for more accurate recent news and achievements
current_year = datetime.now().year
current_month = datetime.now().month
current_date_str = datetime.now().strftime("%Y-%m-%d")

# Enhanced instructions for search and scraping agents with specific focus on schools and companies
search_instructions = [
    '''CRITICAL WORKFLOW FOR INFORMATION RETRIEVAL:
    1. Use multiple search engines to gather latest information,
    2. Cross-reference and validate data from at least 3 different sources,
    3. present information that cannot be verified with search results with a tag not verified,
    4. Use Crawl4ai for each query for deep extraction of information related to every query,
    5. ALWAYS provide direct source URLs and attribution for every piece of information,
    6. When you find relevant websites, use web scraping tools to extract detailed information,
    7. Format information in a consistent, readable manner,
    8. Show the information in table which is possible to be shown in table,
    ''',
    
    '''MANDATORY TABLE FIELDS FOR ALL QUERIES:
    For ANY entity (schools, colleges, companies, organizations, locations), you MUST include these fields in your table:
    - Official Website of schools/colleges/companies/organizations/locations
    - Contact Details of schools/colleges/companies/organizations/locations
    
    These fields are REQUIRED''',
    
    f'''For school or college queries, mandatorily create a comprehensive table with:
    - Institution Name (Latest Official Name),
    - Official Website (of school or college),
    - Contact Details (of school or college),
    - Established Year (Verified from Multiple Sources),
    - Location (Current, Precise Location),
    - Type (Public/Private - Most Recent Status),
    - Total Student Enrollment (Most Recent Academic Year),
    - Annual Tuition Fees (Current Academic Year),
    - Top Programs Offered (Updated Curriculum),
    - Accreditation Status (Most Recent Certification),
    - Average Campus Placement Rate (This column is only for colleges),
    - Recent Notable Achievements in detail (Within Last 6 MONTHS - focusing on {current_year} data),
    - Campus Facilities (Current Infrastructure)
    
    Always include direct source URLs for each piece of information.''',
    
    f'''For company queries, create a comprehensive table with:
    - Company Name (Latest Official Name),
    - Official Website ,
    - Contact Details,
    - Founded Year (Verified Date),
    - Headquarters Location (Current Address),
    - Industry Sector (Most Recent Classification),
    - Number of Employees (Latest Reported Count),
    - Annual Revenue (Most Recent Financial Year),
    - Average Salary Range (Current Market Data),
    - Top Job Roles (Updated Job Market Trends),
    - Company Culture Rating (Recent Employee Feedback),
    - Recent Major News/Developments (Last 3 MONTHS only - focusing on {current_year} data),
    - Key Products/Services (Current Offerings)
    
    Always include direct source URLs for each piece of information.''',
    
    '''ANTI-HALLUCINATION GUIDELINES:
    - present information that cannot be verified with search results with a tag Not Verified
    - ALWAYS provide source URLs for each piece of information
    - Include the date when the information was retrieved
    - For conflicting information, present all perspectives with source links
    - Do not try to fill gaps with educated guesses
    - Present exact quotes from sources when possible
    - Indicate confidence level for each piece of information (High/Medium/Low)
    - Use phrases like "According to [source]..." rather than presenting information as definitive facts''',
    
    '''CRITICAL FUSION INSTRUCTION:
    - Only combine web search results with LLM's contextual knowledge when search results are sparse,
    - If web search provides specific data points, rely primarily on these verified points,
    - Use LLM knowledge ONLY to organize and structure information, not to supplement it,
    - Highlight any discrepancies between search results and existing knowledge,
    - When in doubt, trust the search results over pre-existing knowledge''',

    f'''MANDATORY INSTRUCTION FOR ALL SCHOOL QUERIES:
    You MUST return ALL data points for the comprehensive table including:
    - Institution Name (Latest Official Name),
    - Official Website (of that school),
    - Contact Details (of that school),
    - Established Year (Verified from Multiple Sources),
    - Location (Current, Precise Location),
    - Type (Public/Private - Most Recent Status),
    - Total Student Enrollment (Most Recent Academic Year),
    - Annual Tuition Fees (Current Academic Year),
    - Top Programs Offered (Updated Curriculum),
    - Accreditation Status (Most Recent Certification),
    - Recent Notable Achievements (Within Last 6 MONTHS - focusing on {current_year} data only),
    - Campus Facilities (Current Infrastructure)
    
    If any data point cannot be found, indicate with "Data not available" but NEVER omit columns''',

    f'''MANDATORY INSTRUCTION FOR ALL COLLEGES OR UNIVERSITIES QUERIES:
    You MUST return ALL data points for the comprehensive table including:
    - Institution Name (Latest Official Name),
    - Official Website (of that college or universities),
    - Contact Details (of that college or universities),
    - Established Year (Verified from Multiple Sources),
    - Location (Current, Precise Location),
    - Type (Public/Private - Most Recent Status),
    - Total Student Enrollment (Most Recent Academic Year),
    - Annual Tuition Fees (Current Academic Year),
    - Top Programs Offered (Updated Curriculum),
    - Accreditation Status (Most Recent Certification),
    - Average Campus Placement Rate (Latest Available Data),
    - Recent Notable Achievements (Within Last 6 MONTHS - focusing on {current_year} data only),
    - Campus Facilities (Current Infrastructure)
    
    If any data point cannot be found, indicate with "Data not available" but NEVER omit columns''',
    
    '''SOURCE ATTRIBUTION REQUIREMENTS:
    After the main table, you MUST include a "Sources" section that follows these rules:
    
    1. List every source used for the information with:
       - Full URL of the source website
       - Date the page was last accessed
       - Brief description of what information was obtained from this source
       
    2. For each piece of information in the table, indicate in brackets which source it came from
       - Example: "Annual Revenue: $2.5 million [Source 3]"
       - This allows users to verify the information themselves
    
    3. For conflicting information, include all sources that provided different data points
       - Example: "Employee Count: 500 [Source 1] or 550 [Source 2]"''',
    
    f'''CRITICAL NEWS SECTION REQUIREMENTS:
    For ALL queries about any entity, you MUST include a "Recent News" section that follows these rules:
    
    1. RECENCY: Search specifically for news published within the LAST 3 MONTHS ONLY, using date-specific search terms
       - Example search: "[entity name] news {current_year}" or "[entity name] recent news last 3 months"
       - Use specific date ranges in your searches (e.g., "after:{current_year}-{current_month-3}-01")
       - Use Crawl4ai to extract news sections from the entity's official website
       - Prioritize news from the most recent month when available
       - Do NOT include any news from previous years unless absolutely nothing from {current_year} is available
    
    2. BALANCE: You MUST include BOTH positive and negative news when available
       - Include at least 1 positive development (achievements, growth, awards)
       - Include at least 1 critical or challenging news item (controversies, setbacks, criticisms)
       - If only positive or only negative news exists, note this explicitly
    
    3. FORMATTING: Each news item MUST include:
       - Headline (exact as published)
       - Publication date (including month and year, with exact date when available)
       - Source (publication name with link if available)
       - Brief 1-2 sentence summary
       - Label as [POSITIVE] or [CHALLENGING] at the beginning of each item
    
    4. VERIFICATION: Cross-reference news from multiple sources when possible
    
    5. MINIMUM REQUIREMENT: Include at least 3-5 news items total from {current_year} only
       - If fewer than 3 recent news items from {current_year} can be found, explicitly state: "Limited recent news is available for this entity. The following represents the most current information found:"
    
    Use specific search queries like "[entity name] news {current_year}" and "[entity name] achievement {current_year}" to ensure the most recent coverage.''',
    
    '''INFORMATION CONFIDENCE INDICATORS:
    For each section of your response, indicate the confidence level based on the quality and quantity of sources:
    
    - HIGH CONFIDENCE: Information verified from 3+ reputable sources including official websites
    - MEDIUM CONFIDENCE: Information found in 1-2 reputable sources
    - LOW CONFIDENCE: Information found only in user-generated content or forums
    - NO CONFIDENCE: No information found (use "Data not available")
    
    These confidence indicators must be included at the beginning of each major section of your response.'''
]

# Enhanced Google Search agent with web scraping capabilities
search_agent_GoogleSearch = Agent(
    model=Groq(id="deepseek-r1-distill-llama-70b"),
    role="Information retrieval specialist using Google Search with web scraping and general knowledge capabilities",
    tools=[
        GoogleSearch(),
        Crawl4aiTools(max_length=None),
    ],
    description="You retrieve accurate and up-to-date information from Google Search results and can scrape website content when needed. You can also answer general knowledge questions and are particularly valuable for recent information.",
    instructions=search_instructions,
    stream=False,
    show_tool_calls=False
)

# Enhanced DuckDuckGo agent with web scraping capabilities
search_agent_DuckDuckGO = Agent(
    model=Groq(id="deepseek-r1-distill-llama-70b"),
    role="Information retrieval specialist using DuckDuckGo with web scraping and general knowledge capabilities",
    tools=[
        DuckDuckGo(),
        Crawl4aiTools(max_length=None),
    ],
    description="You retrieve accurate and up-to-date information from DuckDuckGo search results and can scrape website content when needed. You can also answer general knowledge questions and are particularly good at privacy-respecting searches.",
    instructions=search_instructions,
    stream=False,
    show_tool_calls=False
)

# Enhanced Baidu Search agent with web scraping capabilities
search_agent_BaiduSearch = Agent(
    model=Groq(id="deepseek-r1-distill-llama-70b"),
    role="Information retrieval specialist using Baidu Search with web scraping and general knowledge capabilities",
    tools=[
        BaiduSearch(),
        Crawl4aiTools(max_length=None),
    ],
    description="You retrieve accurate and up-to-date information from Baidu search results and can scrape website content when needed - particularly valuable for information about Asian entities and general knowledge related to Asia.",
    instructions=search_instructions,
    stream=False,
    show_tool_calls=False
)

# Enhanced main agent instructions for information fusion
main_agent_instructions = [
    f'''MANDATORY TABLE FORMAT INSTRUCTION FOR ALL SCHOOL/COLLEGE QUERIES:
    When ANY query involves a school, college, or educational institution, you MUST create a comprehensive table with EXACTLY these columns:
    
    | Institution Name | Official Website | Contact Information | Established Year | Location | Type | Total Student Enrollment | Annual Tuition Fees | Top Programs Offered | Accreditation Status | Average Campus Placement Rate | Recent Notable Achievements | Campus Facilities |
    
    in case if query is related to School, then do not include the Average Campus Placement Rate column
    CRITICAL: Website and contact information are REQUIRED fields:
    - Official Website: URL
    - Contact Information: Phone number or anything
    
    ACTIVELY search for these two pieces of information as a TOP PRIORITY using:
    - The institution's official website
    - "Contact Us" pages
    - Directory listings
    - Social media profiles
    - Google Maps
    
    FOR RECENT NOTABLE ACHIEVEMENTS:
    - ONLY include achievements from {current_year}
    - Search with specific date filters using "after:{current_year}-01-01"
    - Use search terms like "[institution name] achievement {current_year}" or "[institution name] award {current_year}"
    - Use Crawl4ai on the institution's "News" or "Announcements" pages
    
    NO OTHER TABLE FORMAT IS ACCEPTABLE for educational institution queries. Do not deviate from this format.
    Only if after exhaustive searching you cannot find website or contact info, use "Data not available".
    
    After the table, you MUST provide a "Recent News" section with both positive and negative news for EACH institution in your results, focusing ONLY on {current_year} news.''',
    
    f'''MANDATORY TABLE FORMAT INSTRUCTION FOR ALL COMPANY QUERIES:
    When ANY query involves a company or business, you MUST create a comprehensive table with EXACTLY these columns:
    
    | Company Name | Official Website | Contact Information | Founded Year | Headquarters Location | Industry Sector | Number of Employees | Annual Revenue | Average Salary Range | Top Job Roles | Company Culture Rating | Recent Major News | Key Products/Services |
    
    CRITICAL: Website and contact information are REQUIRED fields:
    - Official Website: Full URL starting with http:// or https://
    - Contact Information: Phone number with country/area code or email address
    
    ACTIVELY search for these two pieces of information as a TOP PRIORITY using:
    - The company's official website
    - "Contact Us" pages
    - Business directories
    - Social media profiles
    - Google Maps
    
    FOR RECENT MAJOR NEWS:
    - ONLY include news from {current_year}
    - Search with specific date filters using "after:{current_year}-01-01"
    - Use search terms like "[company name] news {current_year}" or "[company name] announcement {current_year}"
    - Use Crawl4ai on the company's "News" or "Press Releases" pages
    
    NO OTHER TABLE FORMAT IS ACCEPTABLE for company queries. Do not deviate from this format.
    Only if after exhaustive searching you cannot find website or contact info, use "Data not available".
    
    After the table, you MUST provide a "Recent News" section with both positive and negative news for EACH company in your results, focusing ONLY on {current_year} news.''',
    
    '''CRITICAL WORKFLOW FOR INFORMATION RETRIEVAL:
        1. Use multiple search engines to gather latest information,
        2. Cross-reference and validate data from at least 3 different sources,
        3. Combine web search results with contextual LLM knowledge,
        4. Use Crawl4ai for each query for deep extraction of information related to every query,
        5. Always provide sources for your information,
        6. When you find relevant websites, use web scraping tools to extract detailed information,
        7. Format information in a consistent, readable manner,
        8. Show the information in table which is possible to be shown in table''',
    
    # Information quality and citation
    "Always provide accurate information with clear attribution to sources",
    "Include direct links to source websites when available",
    "Evaluate source credibility and prioritize official websites and reputable sources",
    
    # Query analysis and search engine selection
    "Analyze queries deeply to identify subject domain, geographic relevance, and recency requirements",
    "Use multiple search engines for global topics to ensure comprehensive coverage",
    "For Asia-specific queries, prioritize Baidu Search",
    "For privacy-sensitive topics, prioritize DuckDuckGo",
    "For general global queries, prefer Google Search",
    
    # Web scraping and information synthesis
    "Use web scraping tools strategically - Crawl4ai for deep content extraction from key pages",
    "Synthesize information across multiple sources to provide a complete picture",
    "When sources conflict, present all perspectives with your assessment of reliability",
    "Format extracted data in tables whenever the information is structured and comparable",
    
    # Domain-specific organization
    "For companies: Structure as Company Overview, Products/Services, Leadership, Financials, Recent News",
    "For educational institutions: Always use the MANDATORY table format specified at the top",
    "For locations/venues: Organize as Address, Opening Hours, Offerings, Reviews, Contact Information",
    "For products: Show Features, Pricing, Availability, Comparisons, Customer Reviews",
    "For events: Include Dates, Location, Participants, Schedule, Registration/Ticket Information",
    
    # Recency handling (modified to always use search tools)
    "MANDATORY: For ALL queries, ALWAYS use search tools to retrieve the most up-to-date information",
    "Never rely solely on built-in knowledge for any information",
    "Always verify information through search tools regardless of query content",
    
    # Response quality
    "Begin responses with a direct, concise answer to the query before providing supporting details",
    "Prioritize readability with clear headings, short paragraphs, and bullet points for lists",
    "Use tables to compare multiple entities or organize structured information",
    "Include both summary information and detailed facts to accommodate different user needs",
    "Provide perspective on information significance when relevant (e.g., whether a statistic is high/low)",
    
    # News reporting requirement
    f"MANDATORY: Include a 'Recent News' section after the table information for EACH entity mentioned",
    f"For EACH entity, report BOTH positive and negative news from {current_year} ONLY",
    f"For each news item, include exact date (if available), headline, brief summary, and source",
    f"Clearly label each news item as 'POSITIVE' or 'CHALLENGING'",
    f"Balance perspectives by including at least one positive and one negative news item for each entity",
    f"Organize news items chronologically with newest items first",
    f"Use date-restricted searches to find the newest information possible",
    f"Use search queries with specific date ranges like 'after:{current_year}-01-01'",
    
    # Special handling
    "For numerical data, include context (e.g., industry averages, historical trends) when available",
    "For technical topics, provide both simplified explanations and detailed information",
    "When information appears outdated, explicitly note this and search for more recent sources",
    "For controversial topics, present multiple viewpoints with balanced treatment",
    
    # Process transparency
    "Clearly indicate which search engines were used to retrieve information",
    "Note when information comes from web scraping versus search results",
    "Acknowledge information gaps when searches don't yield complete answers",
    "Always double-check calculations and factual claims before presenting them",
    "Add the current year to search queries to find the most recent information"
]

# Modified system message template to ensure search tools are used for every query
system_message_template = f"""
You are an advanced information retrieval system designed to provide ONLY verified information. For EVERY query, follow this protocol EXACTLY:

1. You MUST use your search tools for ALL queries to provide the most current and accurate information.
   - Do not rely on your pre-trained knowledge for ANY information
   - NEVER state "As of my last update" or similar phrases
   - ALWAYS verify information through search, regardless of the query content
   - NEVER invent or hallucinate information that cannot be verified through search results

2. For the query: "{{user_query}}"
   - You MUST use search tools to gather current information
   - Combine search results with your knowledge ONLY for organization and structure
   - Verify ALL facts, figures, and statements through search
   - Use "Data not available" for any information that cannot be verified

3. Use multiple search engines to cross-reference information:
   - Google Search for general global queries
   - Baidu Search for Asia-specific information
   - DuckDuckGo for privacy-sensitive topics
   - ALWAYS show which search engine provided which information

4. CRITICAL: For ANY school or college queries, you MUST create a table with EXACTLY these columns in this EXACT order:
   | Institution Name | Official Website | Contact Details | Established Year | Location | Type | Total Student Enrollment | Annual Tuition Fees | Top Programs Offered | Accreditation Status | Average Campus Placement Rate | Recent Notable Achievements | Campus Facilities |
   
   - Institution Name: Latest official name
   - Official Website: REQUIRED - Working URL to the institution's site with http:// or https://
   - Contact Details: REQUIRED - Current phone number, email address
   - Established Year: Verified from multiple sources
   - Location: Current, precise location
   - Type: Public/Private - most recent status
   - Total Student Enrollment: Most recent academic year
   - Annual Tuition Fees: Current academic year
   - Top Programs Offered: Updated curriculum
   - Accreditation Status: Most recent certification
   - Average Campus Placement Rate: Latest available data (only for colleges)
   - Recent Notable Achievements: Must be from {current_year} ONLY - use date-restricted searches
   - Campus Facilities: Current infrastructure
   
   For ANY missing information, write "Data not available" in the cell. NEVER omit columns or change their order.
   Add source attribution for each piece of information [Source #].

5. MANDATORY SOURCES SECTION: After any table or detailed information, you MUST include a "Sources" section that lists:
   - Full URLs of all websites used
   - Date the information was accessed
   - Brief description of what information was obtained from each source
   - Number each source so it can be referenced in the body of the text [Source #]

6. MANDATORY RECENT NEWS SECTION: For ALL queries (schools, colleges, companies, or any entity), you MUST include a "Recent News" section after the main information with:
   - News items MUST be from {current_year} ONLY - use specific date-restricted searches
   - At least 3-5 news items when available
   - News items MUST include BOTH positive developments AND critical/challenging news
   - Each news item must be labeled as [POSITIVE] or [CHALLENGING] at the beginning
   - Include for each: headline, exact publication date (day/month/year if available), source URL, and 1-2 sentence summary
   - Use specific search queries like "[entity name] news {current_year}" and "[entity name] achievement {current_year}"
   - Use date-specific search parameters like "after:{current_year}-01-01"
   - If limited recent news is available, explicitly state this but still provide what you can find

7. OFFICIAL WEBSITE AND CONTACT DETAILS CHECK:
   - Double-check that Official Website and Contact Details are included in the table
   - For Official Website, provide complete URL (including https://)
   - For Contact Details, provide phone, email, and/or social media when available
   - These fields are REQUIRED for ALL entity-based queries

8. CONFIDENCE INDICATORS:
   - Label each major section with confidence level based on source quality and quantity:
   - HIGH CONFIDENCE: Information verified from 3+ reputable sources including official websites
   - MEDIUM CONFIDENCE: Information found in 1-2 reputable sources 
   - LOW CONFIDENCE: Information found only in user-generated content or forums
   - NO CONFIDENCE: No information found (use "Data not available")

9. After searching, synthesize a complete response that integrates all information sources with proper source attribution.

10. FINAL CHECK: Before submitting your response, verify:
   - Your table has ALL REQUIRED COLUMNS in the EXACT order specified above
   - Official Website and Contact Details columns are properly filled
   - You've included the Sources section with numbered references
   - You've included the Recent News section with BOTH positive and challenging news items
   - All news items are from {current_year} ONLY
   - Each major section has confidence indicators
   - You've used "Data not available" rather than inventing information
"""

def validate_education_query_response(response_text, query):
    # Simple detection for education-related queries
    education_keywords = ["school", "college", "university", "institute", "campus", 
                         "education", "academic", "student", "faculty", "course"]
    
    is_education_query = any(keyword.lower() in query.lower() for keyword in education_keywords)
    
    # Check if the response includes a Sources section
    has_sources_section = "Sources:" in response_text or "SOURCES:" in response_text
    
    if not has_sources_section:
        sources_reminder = f"""

**MISSING INFORMATION: A "Sources" section should be included listing all websites used for information gathering with URLs and access dates.**
        """
        response_text += sources_reminder
    
    # Check if confidence indicators are included
    has_confidence_indicators = any(level in response_text for level in ["HIGH CONFIDENCE:", "MEDIUM CONFIDENCE:", "LOW CONFIDENCE:"])
    
    if not has_confidence_indicators:
        confidence_reminder = """

**MISSING INFORMATION: Confidence indicators (HIGH/MEDIUM/LOW) should be included for each major section based on source quality.**
        """
        response_text += confidence_reminder
    
    if not is_education_query:
        # Check if the response has "Official Website" and "Contact Details" if it's any type of entity
        has_website = "Official Website" in response_text
        has_contact = "Contact Details" in response_text
        
        if not (has_website and has_contact):
            general_reminder = """

**MISSING INFORMATION: Information about any entity should include Official Website and Contact Details. Please request this information if needed.**
            """
            response_text += general_reminder
        
        # Check if the response has a balanced news section
        has_news_section = "Recent News" in response_text or "RECENT NEWS" in response_text
        has_positive = "[POSITIVE]" in response_text
        has_challenging = "[CHALLENGING]" in response_text
        
        if not has_news_section or not (has_positive and has_challenging):
            news_reminder = f"""

**MISSING INFORMATION: A Recent News section should be included with both positive and challenging news items from {current_year} only. Please request this information if needed.**
            """
            response_text += news_reminder
            
        return response_text
    
    # For education queries, check if the response has the required columns
    required_columns = [
        "Institution Name", "Official Website", "Contact Details", "Established Year", "Location", "Type", 
        "Total Student Enrollment", "Annual Tuition Fees", "Top Programs Offered",
        "Accreditation Status", "Average Campus Placement Rate", 
        "Recent Notable Achievements", "Campus Facilities"
    ]
    
    # Check if the response has a balanced news section
    has_news_section = "Recent News" in response_text or "RECENT NEWS" in response_text
    has_positive = "[POSITIVE]" in response_text
    has_challenging = "[CHALLENGING]" in response_text
    
    # If there's a table but missing required columns, add a correction note
    if "| Institution Name |" not in response_text or len(required_columns) > response_text.count("|") / 2:
        correction_note = """
        
**MISSING INFORMATION: The table provided is incomplete. A comprehensive educational institution table should include the following columns:**

| Institution Name | Official Website | Contact Details | Established Year | Location | Type | Total Student Enrollment | Annual Tuition Fees | Top Programs Offered | Accreditation Status | Average Campus Placement Rate | Recent Notable Achievements | Campus Facilities |

Please request more detailed information if needed.
        """
        response_text += correction_note
    
    # If there's no balanced news section, add a reminder
    if not has_news_section or not (has_positive and has_challenging):
        news_reminder = f"""

**MISSING INFORMATION: A Recent News section should be included with both positive [POSITIVE] and challenging [CHALLENGING] news items from {current_year} only. Please request this information if needed.**
        """
        response_text += news_reminder
    
    # Add anti-hallucination disclaimer if needed
    disclaimer = f"""

**INFORMATION VERIFICATION NOTICE: All information provided has been gathered through search tools and web scraping as of {current_date_str}. Any field marked as "Data not available" indicates that information could not be verified from reliable sources. Please consult official websites for the most accurate and up-to-date information.**
        """
    response_text += disclaimer
    
    return response_text

# Function to validate company query responses
def validate_company_query_response(response_text, query):
    # Simple detection for company-related queries
    company_keywords = ["company", "business", "corporation", "firm", "enterprise", 
                        "corporate", "industry", "organization", "startup"]
    
    is_company_query = any(keyword.lower() in query.lower() for keyword in company_keywords)
    
    if not is_company_query:
        return response_text
    
    # Check if the response has the required columns for companies
    if "| Company Name |" not in response_text or "| Official Website |" not in response_text or "| Contact Information |" not in response_text:
        correction_note = """
        
**NOTE: The table provided is incomplete. A comprehensive company table should include the following columns:**

| Company Name | Official Website | Contact Information | Founded Year | Headquarters Location | Industry Sector | Number of Employees | Annual Revenue | Average Salary Range | Top Job Roles | Company Culture Rating | Recent Major News | Key Products/Services |

Please request more detailed information if needed.
        """
        return response_text + correction_note
    
    # Check if there's a news section with both positive and negative news
    if "Recent News" not in response_text or ("POSITIVE" not in response_text and "Positive" not in response_text) or ("NEGATIVE" not in response_text and "Negative" not in response_text and "CHALLENGING" not in response_text and "Challenging" not in response_text):
        news_note = f"""

**NOTE: The response should include a "Recent News" section with both positive and negative news items from {current_year} only for each company mentioned.**

Please request this information if needed.
        """
        return response_text + news_note
        
    return response_text


# Function to clean system instructions from the response
def clean_system_instructions(response_text):
    # Patterns to identify and remove system instructions
    patterns = [
        r"As an advanced information retrieval system.*?protocol EXACTLY:",
        r"YOU MUST use your search tools.*?information\.",
        r"NEVER state \"As of my last update\".*?phrases",
        r"ALWAYS verify information through.*?content",
        r"CRITICAL: For ANY school or college queries.*?order\.",
        r"MANDATORY: After the table.*?first",
        r"YOUR RESPONSE MUST CONTAIN.*?requested",
        r"I'll use my search tools to gather.*?Query:",
        r"I must use search tools to gather.*?information\.",
        r"For your query about.*?search tools\.",
        r"I'll now search for the most up-to-date information.*?query\.",
        r"Let me search for information about.*?\.",
        r"Following the required format for educational institutions.*?\.",
        r"I'll make sure to include both positive and negative news.*?\.",
        r"I'll ensure I don't include system instructions.*?\.",
        r"Now, let me gather information using my search tools.*?one moment\.",
        r"Website and contact information are TOP PRIORITY fields.*?pages\.",
        r"I need to use search tools for this query.*?\.",
        r"I'll actively search for the official website and contact information.*?\.",
        r"I'll make sure to include news for each entity.*?\.",
        r"Each news item will be clearly labeled as.*?\.",
        r"Let me search for the most current information.*?\.",
        r"Before providing my response.*?\.",
        r"I understand I need to provide comprehensive information.*?\.",
        r"I'll get started on your query.*?\.",
        r"I'll ALWAYS cite my sources.*?\.",
        r"These instructions are VERY IMPORTANT.*?\.",
        r"Using my search tools to gather current information.*?\.",
        r"I need to conduct web searches for this.*?\.",
        r"I'm using search tools to gather this information.*?\.",
        r"I'll make sure to include website and contact information.*?\.",
        r"I'm searching for both positive and negative news.*?\.",
        r"I'll be sure to format my response according to.*?\.",
        r"For this query, I need to.*?\.",
        r"I must create a comprehensive table.*?\.",
        r"Let me gather the requested information.*?\.",
        r"I'm using search tools to find the most up-to-date information.*?\.",
        r"I'll use Crawl4ai to extract detailed information.*?\."
    ]
    
    # Apply the patterns to clean the response
    cleaned_response = response_text
    for pattern in patterns:
        cleaned_response = re.sub(pattern, "", cleaned_response, flags=re.DOTALL)
    
    # Remove any resulting double spaces or newlines
    cleaned_response = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response)
    cleaned_response = re.sub(r'  +', ' ', cleaned_response)
    
    return cleaned_response.strip()

# Function to enforce website and contact information inclusion
def enforce_website_contact_info(response_text, query):
    # If the response already has website and contact info, return as is
    if ("| Official Website |" in response_text and "| Contact Information |" in response_text and 
        not ("Official Website | Data not available" in response_text and "Contact Information | Data not available" in response_text)):
        return response_text
    
    # Add a specific warning about website and contact information
    warning = """
    
**IMPORTANT: The results should include Official Website and Contact Information for each entity mentioned. Please ensure this critical information is included in all tables.**
    """
    
    return response_text + warning

# Modified agent to use search tools for every query
class AlwaysSearchAgent(Agent):
    def run(self, message, **kwargs):
        # Modified instruction to emphasize preserving the original query
        enriched_message = f"CRITICAL: YOU MUST USE SEARCH TOOLS and web scraping tools for this query. YOU MUST FIND AND INCLUDE OFFICIAL WEBSITE URLs AND CONTACT INFORMATION for all entities. YOU MUST PROVIDE BOTH POSITIVE AND NEGATIVE NEWS for all entities mentioned. DO NOT add year on your own, but you are allowed to do other changes for functionality. Query: {message}"
        response = super().run(enriched_message, **kwargs)
        
        # If it's not streaming, post-process the response
        if not kwargs.get("stream", False):
            # First validate the educational and company query responses
            response = validate_education_query_response(response, message)
            response = validate_company_query_response(response, message)
            # Enforce website and contact information
            response = enforce_website_contact_info(response, message)
            # Then clean out any system instructions
            response = clean_system_instructions(response)
        
        return response

agent_team = AlwaysSearchAgent(
    name="Information Research Team",
    model=Groq(id="deepseek-r1-distill-llama-70b"),
    role="Team coordinator that manages information retrieval across multiple search platforms and web scraping tools for ALL queries",
    team=[search_agent_GoogleSearch, search_agent_BaiduSearch, search_agent_DuckDuckGO],
    instructions=main_agent_instructions,
    storage=SqlAgentStorage(table_name="information_research_team", db_file="agents.db"),
    add_history_to_messages=False,
    stream=False,
    show_tool_calls=False,
    markdown=False,
    system_message=system_message_template.format(user_query="Example query")
)

# Override the run method to inject the actual query into the system message
original_run = agent_team.run
def enhanced_run(message, **kwargs):
    agent_team.system_message = system_message_template.format(user_query=message)
    return original_run(message, **kwargs)
agent_team.run = enhanced_run

# Stream handler class for EventSource responses
class EventStreamHandler:
    def __init__(self):
        self.chunks = []
        self.tool_calls = []

    def handle_chunk(self, chunk):
        """Process a chunk from the agent"""
        if isinstance(chunk, dict) and "type" in chunk and chunk["type"] == "tool_call":
            # Handle tool call (we might skip or store it)
            self.tool_calls.append(chunk)
            return json.dumps({"tool_call": chunk}) + "\n\n"
        else:
            # Handle text chunk
            self.chunks.append(chunk)
            return json.dumps({"chunk": chunk}) + "\n\n"

    def handle_stream(self, message, response_handler=None):
        """Generate an event stream for the given message"""
        def stream_generator():
            try:
                # Run the agent with a streaming callback
                agent_team.run(
                    message, 
                    stream_handler=lambda chunk: self._process_chunk(chunk, response_handler)
                )
                
                # Signal the end of the stream
                yield "data: " + json.dumps({"done": True}) + "\n\n"
            
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                yield "data: " + error_data + "\n\n"
        
        if response_handler:
            for chunk in stream_generator():
                response_handler(chunk)
            return None
        else:
            return stream_generator()
    
    def _process_chunk(self, chunk, response_handler):
        """Process a chunk and either yield it or pass it to a response_handler"""
        event_data = ""
        
        if isinstance(chunk, dict) and "type" in chunk and chunk["type"] == "tool_call":
            # It's a tool call
            self.tool_calls.append(chunk)
            event_data = "data: " + json.dumps({"tool_call": chunk}) + "\n\n"
        else:
            # It's a text chunk
            self.chunks.append(chunk)
            event_data = "data: " + json.dumps({"chunk": chunk}) + "\n\n"
        
        if response_handler:
            response_handler(event_data)
        else:
            if event_data:
                return event_data
        
        print("Processed Chunk:", chunk)
        return chunk

# @app.route('/')
# def index():
#     return render_template('index.html')


@app.route('/api/query', methods=['POST'])
def process_query():
    """
    Non-streaming endpoint that:
      1) Runs the agent (no streaming).
      2) Extracts only the substring inside content='...'
      3) Returns that clean substring as JSON to the frontend.
    """
    data = request.json
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Run agent in non-stream mode
        response = agent_team.run(query, stream=False)

        # Convert to string if needed
        text_response = response if isinstance(response, str) else str(response)

        # Find all matches in case there's more than one
        matches = re.findall(r"content='([^']*)'", text_response)
        if matches:
            # Join or pick the last one, depending on your preference
            # For example, just take the last match:
            final_content = matches[-1].strip()
        else:
            final_content = ""

        return jsonify({"success": True, "response": final_content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/stream', methods=['GET', 'POST'])
def stream_response():
    if request.method == 'GET':
        query = request.args.get('query', '')
    else:  # POST
        data = request.json
        query = data.get('query', '')

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Import Google Generative AI
    from google import genai

    # Initialize the Generative AI client
    client = genai.Client(api_key=GOOGLE_API_KEY)

    def generate():
        try:
            # Accumulate all chunks first
            total_chunks = []

            # Run the agent in streaming mode
            for chunk in agent_team.run(query, stream=True):
                # Convert chunk to string, handling different possible types
                text_chunk = chunk if isinstance(chunk, str) else str(chunk)

                # REGEX to extract content from tool call or response
                match = re.search(r"content='([^']*)'", text_chunk)
                if match:
                    # Extract the content
                    content_chunk = match.group(1).strip()
                    
                    # Add meaningful chunks to total_chunks
                    if content_chunk:
                        total_chunks.append(content_chunk)

            # Combine all chunks
            all_chunks = " ".join(total_chunks)
            
            # Use Google Generative AI to format and process the chunks
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents='''Reformat this text to have:
                - Clear line breaks between sections
                - Proper word spacing
                - Readable paragraph structure
                - No unnecessary concatenation of words
                - Use markdown formatting where appropriate
                
                
                Text to format: ''' + all_chunks
            )
            
            # Final processed data
            final_data = response.text
            
            # Validate education query responses
            education_keywords = ["school", "college", "university", "institute", "campus", 
                                "education", "academic", "student", "faculty", "course"]
            is_education_query = any(keyword.lower() in query.lower() for keyword in education_keywords)
            
            if is_education_query:
                required_columns = [
                    "Institution Name", "Established Year", "Location", "Type", 
                    "Total Student Enrollment", "Annual Tuition Fees", "Top Programs Offered",
                    "Accreditation Status", "Average Campus Placement Rate", 
                    "Recent Notable Achievements", "Campus Facilities"
                ]
                
                missing_columns = []
                for col in required_columns:
                    if col not in final_data:
                        missing_columns.append(col)
                
                if missing_columns:
                    correction_note = "\n\n**NOTE: The table is missing these required columns: " + ", ".join(missing_columns) + ". Please request more detailed information if needed.**"
                    final_data += correction_note
            
            # Send the final processed data
            processed_chunk = json.dumps({"chunk": final_data})
            yield "data: " + processed_chunk + "\n\n"

            # Signal end of stream
            done_data = json.dumps({"done": True})
            yield "data: " + done_data + "\n\n"

        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield "data: " + error_data + "\n\n"

    return Response(generate(), mimetype='text/event-stream')


from pymongo import MongoClient


MONGODB_URI = os.environ.get('MONGODB_URI')
if not MONGODB_URI:
    raise Exception("MONGODB_URI not set in environment variables")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client['AI-Search-Assistant']  # replace with your database name
users_collection = db['users']

@app.route('/webhook', methods=['POST'])
def clerk_webhook():
    try:
        # Verify Clerk webhook secret
        clerk_secret = os.environ.get('CLERK_WEBHOOK_SECRET')
        if not clerk_secret:
            return jsonify({"message": "Webhook secret not configured"}), 500

        data = request.get_json()
        print("Received webhook data:", data)
        
        event_type = data.get("type")
        if event_type in ["user.created", "user.updated", "user.deleted"]:
            user_data = data.get("data", {})
            clerk_id = user_data.get("id")
            email_addresses = user_data.get("email_addresses", [])
            email = email_addresses[0].get("email_address") if email_addresses else None
            first_name = user_data.get("first_name")
            last_name = user_data.get("last_name")
            full_name = f"{first_name} {last_name}" if first_name and last_name else None
            image_url = user_data.get("image_url")

            if event_type == "user.deleted":
                # Remove user from database if deleted
                users_collection.delete_one({"clerkId": clerk_id})
                return jsonify({"message": "User deleted"}), 200

            # Insert or update the user in MongoDB
            users_collection.update_one(
                {"clerkId": clerk_id},
                {"$set": {
                    "clerkId": clerk_id,
                    "email": email,
                    "name": full_name,
                    "imageUrl": image_url
                }},
                upsert=True
            )
            return jsonify({"message": "User processed"}), 200
        else:
            return jsonify({"message": "Event type not handled"}), 200

    except Exception as e:
        print("Error processing webhook:", e)
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    

@app.route('/api/sync-user', methods=['POST'])
def manual_user_sync():
    try:
        data = request.get_json()
        clerk_id = data.get('clerkId')
        
        if not clerk_id:
            return jsonify({"message": "No Clerk ID provided"}), 400
        
        users_collection.update_one(
            {"clerkId": clerk_id},
            {"$set": {
                "clerkId": clerk_id,
                "email": data.get('email'),
                "name": data.get('name'),
                "imageUrl": data.get('imageUrl')
            }},
            upsert=True
        )
        
        return jsonify({"message": "User synced successfully"}), 200
    
    except Exception as e:
        print("Error syncing user:", e)
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    

MONGODB_URI = os.environ.get('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['AI-Search-Assistant']
search_collection = db['search_results']
users_collection = db['users']

@app.route('/api/pushData', methods=['POST'])
def push_search_data():
    try:
        # Get the data from the request
        data = request.json
        
        # Validate required fields (now also ensuring 'searchQuery' is present)
        if not data or 'content' not in data or 'userId' not in data or 'searchQuery' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Find the user in the database to get additional details
        user = users_collection.find_one({"clerkId": data['userId']})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Prepare the search result document with the searchQuery field included
        search_result = {
            "userId": data['userId'],
            "username": user.get('name', 'Unknown User'),
            "email": user.get('email', 'No email'),
            "content": data['content'],
            "searchQuery": data['searchQuery'],  # Inserting the original search query
            "timestamp": datetime.utcnow()
        }
        
        # Insert the search result into MongoDB
        result = search_collection.insert_one(search_result)
        
        return jsonify({
            "message": "Search data stored successfully",
            "documentId": str(result.inserted_id)
        }), 201
    
    except Exception as e:
        print(f"Error storing search data: {e}")
        return jsonify({"error": "Internal server error"}), 500

    
@app.route('/api/get-stored-responses', methods=['POST'])
def get_stored_responses():
    try:
        data = request.get_json()  # or request.json, but get_json is recommended
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({"error": "No user ID provided"}), 400
        
        # Fetch stored responses for this user, sorted by timestamp (desc), limit 50
        stored_responses = list(
            search_collection.find(
                {"userId": user_id},
                {"_id": 1, "content": 1, "timestamp": 1, "searchQuery": 1}
            )
            .sort("timestamp", -1)
            .limit(50)
        )
        
        # Convert timestamp to ISO format and _id to string
        for resp in stored_responses:
            resp['timestamp'] = resp['timestamp'].isoformat()
            resp['_id'] = str(resp['_id'])  # Convert ObjectId to string
        
        return jsonify({"responses": stored_responses}), 200
    
    except Exception as e:
        print(f"Error fetching stored responses: {e}")
        return jsonify({"error": "Internal server error"}), 500



@app.route('/api/delete-response', methods=['DELETE'])
def delete_response():
    try:
        # Use request.get_json() instead of request.json
        data = request.get_json()
        print("Request data is:", data)

        if not data:
            return jsonify({"error": "Missing request data"}), 400

        response_id = data.get('responseId')
        if not response_id:
            return jsonify({"error": "Missing response ID"}), 400

        # Add error handling for ObjectId conversion
        try:
            object_id = ObjectId(response_id)
        except Exception as e:
            print(f"Invalid ObjectId format: {response_id}, error: {e}")
            return jsonify({"error": f"Invalid ID format: {response_id}"}), 400

        result = search_collection.delete_one({'_id': object_id})
        if result.deleted_count == 1:
            return jsonify({"message": "Response deleted successfully"}), 200
        else:
            return jsonify({"error": "Response not found"}), 404

    except Exception as e:
        print(f"Error deleting response: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)