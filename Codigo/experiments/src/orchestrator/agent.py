"""Custom Agent Loop for V2 Experiment — OpenAI SDK integration and tool usage."""

import json
import os
import time

import psycopg2
import requests
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

from .config import DB_CONN, EXEC_URL, GUEST_IP, HEALTH_URL

# Load environment variables from .env if it exists
load_dotenv()


class AgentLoop:
    def __init__(self, api_key=None, model="gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set for V2 experiment.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.messages = []
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self.encoding = tiktoken.encoding_for_model(model)
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "query_db",
                    "description": "Execute a SQL query against the guest PostgreSQL database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "The SQL query to execute."}
                        },
                        "required": ["sql"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_bash",
                    "description": "Execute a bash command inside the guest microVM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The bash command to run."}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_health",
                    "description": "Check the health of the Node.js API server in the guest.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def _get_context_pollution(self):
        """Estimate current context window pollution in tokens."""
        text = ""
        for m in self.messages:
            if hasattr(m, "content") and m.content:
                text += m.content
            elif isinstance(m, dict) and "content" in m:
                text += m.get("content", "") or ""
            # Include tool results as well for better estimation
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    text += str(tc.function)
        
        return len(self.encoding.encode(text))

    def run_tool(self, tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        if name == "query_db":
            try:
                conn = psycopg2.connect(**DB_CONN)
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(args["sql"])
                    results = cur.fetchall() if cur.description else "Success"
                conn.close()
                return json.dumps(results)
            except Exception as e:
                return f"DB Error: {str(e)}"
        
        elif name == "execute_bash":
            try:
                resp = requests.post(
                    EXEC_URL,
                    json={"command": args["command"]},
                    timeout=5
                )
                return resp.text
            except Exception as e:
                return f"Exec Error: {str(e)}"
        
        elif name == "check_health":
            try:
                resp = requests.get(HEALTH_URL, timeout=2)
                return resp.text
            except Exception as e:
                return f"Health Error: {str(e)}"
        
        return "Unknown tool"

    def chat(self, user_input, system_prompt=None):
        if system_prompt and not self.messages:
            self.messages.append({"role": "system", "content": system_prompt})
        
        self.messages.append({"role": "user", "content": user_input})
        
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto",
            )
            
            # Record usage
            self.token_usage["prompt_tokens"] += response.usage.prompt_tokens
            self.token_usage["completion_tokens"] += response.usage.completion_tokens
            
            msg = response.choices[0].message
            self.messages.append(msg)
            
            if not msg.tool_calls:
                return msg.content
            
            for tool_call in msg.tool_calls:
                result = self.run_tool(tool_call)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result
                })

    def get_telemetry(self):
        return {
            "token_consumption": self.token_usage["prompt_tokens"] + self.token_usage["completion_tokens"],
            "prompt_tokens": self.token_usage["prompt_tokens"],
            "completion_tokens": self.token_usage["completion_tokens"],
            "context_pollution": self._get_context_pollution(),
        }
