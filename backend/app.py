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

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# Enhanced instructions for search and scraping agents with specific focus on schools and companies
search_instructions = [
    '''CRITICAL WORKFLOW FOR INFORMATION RETRIEVAL:
    1. Use multiple search engines to gather latest information,
    2. Cross-reference and validate data from at least 3 different sources,
    3. Combine web search results with contextual LLM knowledge,''',
    
    '''For school or college queries, create a comprehensive table with:
    - Institution Name (Latest Official Name),
    - Established Year (Verified from Multiple Sources),
    - Location (Current, Precise Location),
    - Type (Public/Private - Most Recent Status),
    - Total Student Enrollment (Most Recent Academic Year),
    - Annual Tuition Fees (Current Academic Year),
    - Top Programs Offered (Updated Curriculum),
    - Accreditation Status (Most Recent Certification),
    - Average Campus Placement Rate (Latest Available Data),
    - Recent Notable Achievements (Within Last 2 Years),
    - Campus Facilities (Current Infrastructure)
    and also try to include other relevant information apart from table content''',
    
    '''For company queries, create a comprehensive table with:
    - Company Name (Latest Official Name),
    - Founded Year (Verified Date),
    - Headquarters Location (Current Address),
    - Industry Sector (Most Recent Classification),
    - Number of Employees (Latest Reported Count),
    - Annual Revenue (Most Recent Financial Year),
    - Average Salary Range (Current Market Data),
    - Top Job Roles (Updated Job Market Trends),
    - Company Culture Rating (Recent Employee Feedback),
    - Recent Major News/Developments (Last 12 Months)",
    - Key Products/Services (Current Offerings)
    and also try to include other relevant information apart from table content ''',
    
    '''ADVANCED RETRIEVAL GUIDELINES:
    - Prioritize official websites, recent news articles, verified review platforms,
    - Use web scraping to extract detailed, current information,
    - When information conflicts, present multiple perspectives,
    - Indicate source reliability and recency of each data point,
    - Use markdown table formatting for clear presentation,
    - Include sources for each piece of information,
    - Provide context beyond raw data''',
    
    '''CRITICAL FUSION INSTRUCTION:
    ALWAYS combine web search results with LLM's contextual knowledge,
    - If web search provides specific data points, integrate them,
    - Use LLM to provide deeper analysis, historical context,
    - Highlight differences between web data and existing knowledge,
    - Provide a comprehensive, nuanced response'''
]

# Helper function to determine if a query references future events or recent topics
def detect_future_or_recent(query):
    """Determine if a query references future events, recent topics, or dates after 2023"""
    query_lower = query.lower()
    
    # Get current year and create year range to check
    current_year = datetime.now().year
    future_years = [str(year) for year in range(2023, current_year + 10)]
    
    # Check for years in the query
    has_future_year = any(year in query_lower for year in future_years)
    
    # Look for date patterns (e.g., 2025, 2024-2025, etc.)
    year_pattern = r'20(2[3-9]|[3-9][0-9])'  # Matches years 2023-2099
    has_year_match = re.search(year_pattern, query_lower) is not None
    
    # Check for terms indicating recency or future events
    recency_terms = [
        "recent", "latest", "new", "current", "update", "today", "this month", 
        "this year", "next year", "upcoming", "future", "scheduled", 
        "announced", "released", "planned", "will happen", "expected"
    ]
    has_recency_terms = any(term in query_lower for term in recency_terms)
    
    # Sports events often mentioned in future/recent contexts
    sports_terms = ["champions trophy", "world cup", "olympics", "championship", 
                    "tournament", "match", "game", "series", "season"]
    has_sports_terms = any(term in query_lower for term in sports_terms)
    
    # Add specific keywords for schools and companies
    school_terms = ["university", "college", "school", "campus", "institution"]
    company_terms = ["company", "corporation", "startup", "business", "enterprise"]
    
    has_school_terms = any(term in query_lower for term in school_terms)
    has_company_terms = any(term in query_lower for term in company_terms)
    
    # Return True if any condition is met
    return (has_future_year or has_year_match or 
            (has_recency_terms and (has_sports_terms or has_school_terms or has_company_terms)))

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
    stream=True,
    show_tool_calls=True
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
    stream=True,
    show_tool_calls=True
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
    stream=True,
    show_tool_calls=True
)

# Enhanced main agent instructions for information fusion
current_year = datetime.now().year
main_agent_instructions = [
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
    "For educational institutions: Present Programs, Admissions, Rankings, Campus Life, Faculty Highlights",
    "For locations/venues: Organize as Address, Opening Hours, Offerings, Reviews, Contact Information",
    "For products: Show Features, Pricing, Availability, Comparisons, Customer Reviews",
    "For events: Include Dates, Location, Participants, Schedule, Registration/Ticket Information",
    
    # Recency handling (critical)
    f"MANDATORY: For ANY query referencing dates from 2023 onwards, current events, or recent developments, ALWAYS use search tools",
    f"For sports events, tournaments, competitions, championships occurring from {current_year-1} onwards, ALWAYS use search tools",
    "Never rely on built-in knowledge for time-sensitive information like prices, schedules, rankings, or statistics",
    "When terms like 'current', 'latest', 'recent', 'upcoming', 'scheduled', or 'announced' appear in queries, always search",
    
    # Response quality
    "Begin responses with a direct, concise answer to the query before providing supporting details",
    "Prioritize readability with clear headings, short paragraphs, and bullet points for lists",
    "Use tables to compare multiple entities or organize structured information",
    "Include both summary information and detailed facts to accommodate different user needs",
    "Provide perspective on information significance when relevant (e.g., whether a statistic is high/low)",
    
    # Special handling
    "For numerical data, include context (e.g., industry averages, historical trends) when available",
    "For technical topics, provide both simplified explanations and detailed information",
    "When information appears outdated, explicitly note this and search for more recent sources",
    "For controversial topics, present multiple viewpoints with balanced treatment",
    
    # Process transparency
    "Clearly indicate which search engines were used to retrieve information",
    "Note when information comes from web scraping versus search results",
    "Acknowledge information gaps when searches don't yield complete answers",
    "Always double-check calculations and factual claims before presenting them"
]

# System message template for guiding the agent
system_message_template = """
You are an advanced information retrieval system. Before responding to ANY query, follow this protocol EXACTLY:

1. FIRST, analyze if the query references:
   - Any year from 2023 onwards
   - Recent or upcoming events
   - Current status/information that may have changed after 2023
   - Sports events, competitions, or tournaments (especially when timing is unclear)

2. For queries matching ANY of these criteria, you MUST:
   - IMMEDIATELY use your search tools - DO NOT rely on your pre-trained knowledge
   - NEVER state "As of my last update" or similar phrases
   - NEVER guess about post-2023 information based on patterns or expectations

3. For the specific query: "{user_query}"
   - You MUST determine if it matches the criteria in step 1
   - If YES → Use search tools immediately
   - If NO → You may use your general knowledge, but still search when uncertain

4. Remember: For topics like "Champions Trophy 2025" or similar future/recent events, you MUST search rather than stating what you believe based on your training.

5. "Show the information in table which is possible to be shown in table"
"""

class EnhancedAgent(Agent):
    def run(self, message, **kwargs):
        # Check if the message references future events or recent topics
        if detect_future_or_recent(message):
            # Modify the system message to force search for recent/future topics
            enriched_message = f"IMPORTANT: This question is about a future event or references dates after 2023. YOU MUST USE SEARCH TOOLS instead of your built-in knowledge. Query: {message}"
            return super().run(enriched_message, **kwargs)
        return super().run(message, **kwargs)

agent_team = EnhancedAgent(
    name="Information Research Team",
    model=Groq(id="deepseek-r1-distill-llama-70b"),
    role="Team coordinator that manages information retrieval across multiple search platforms and web scraping tools, can answer general knowledge questions, and ensures recent information is verified",
    team=[search_agent_GoogleSearch, search_agent_BaiduSearch, search_agent_DuckDuckGO],
    instructions=main_agent_instructions,
    storage=SqlAgentStorage(table_name="information_research_team", db_file="agents.db"),
    add_history_to_messages=True,
    stream=True,
    show_tool_calls=True,
    markdown=True,
    system_message=system_message_template.format(user_query="Example query")
)




# Change above code only








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
    app.run(debug=True, host='0.0.0.0', port=5000)