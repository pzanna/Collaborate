import json
import os
from datetime import datetime

# Top-level keys
id_ = "create_research_plan"

description = (
    "Generate a detailed research plan from a query and scope using a structured JSON format."
)

agent_type = "ai_service"
model = "grok-3-mini"

system_prompt = (
    "You are a research planning assistant. Provide detailed, structured responses in JSON format."
)

user_prompt_template = """Please create a comprehensive research plan based on the following information:

Title: {topic_title}
Description: {topic_description}
Scope: Comprehensive

Please provide a detailed research plan with:
1. Clear research objectives (3-5 specific goals)
2. Key areas to investigate (4-6 major research domains)
3. Specific questions to answer (5-8 focused research questions)
4. Information sources to consult (academic databases, repositories, etc.)
5. Expected outcomes and deliverables
6. Realistic timeline with phases

Format your response as a JSON object with this exact structure:
{
  "objectives": ["Objective 1", "Objective 2", "Objective 3"],
  "key_areas": ["Area 1", "Area 2", "Area 3", "Area 4"],
  "questions": ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"],
  "sources": ["PubMed", "ArXiv", "Semantic Scholar", "CORE", "CrossRef", "OpenAlex"],
  "outcomes": ["Literature review", "Data analysis", "Experiment design", "Research synthesis", "Final report"]
}

Do NOT include cost or dollar amounts. Be thorough and realistic."""


# Tool keys and nested elements
tool_type = "function"
tool_name = "google_search"
tool_description = (
    "Search the web using Google Custom Search to find recent research, "
    "discover additional relevant studies, and find similar work."
)

tool_param_type = "object"

tool_param_query_type = "string"
tool_param_query_description = "The search query to find relevant research data and studies"

tool_param_num_results_type = "integer"
tool_param_num_results_description = (
    "Number of search results to return (default: 10, max: 10)"
)
tool_param_num_results_default = 10
tool_param_num_results_min = 1
tool_param_num_results_max = 10

tool_param_required = ["query"]

# Tool structure
tools = [
    {
        "type": tool_type,
        "function": {
            "name": tool_name,
            "description": tool_description,
            "parameters": {
                "type": tool_param_type,
                "properties": {
                    "query": {
                        "type": tool_param_query_type,
                        "description": tool_param_query_description
                    },
                    "num_results": {
                        "type": tool_param_num_results_type,
                        "description": tool_param_num_results_description,
                        "default": tool_param_num_results_default,
                        "minimum": tool_param_num_results_min,
                        "maximum": tool_param_num_results_max
                    }
                },
                "required": tool_param_required
            }
        }
    }
]

tool_choice = "auto"
max_tokens = 3000
temperature = 0.6
created_at = datetime.now().isoformat()

# Final config
config = {
    "id": id_,
    "description": description,
    "agent_type": agent_type,
    "model": model,
    "system_prompt": system_prompt,
    "user_prompt_template": user_prompt_template,
    "tools": tools,
    "tool_choice": tool_choice,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "created_at": created_at
}

# Save to file
output_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "create_research_plan.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
