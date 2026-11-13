import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI

from config import settings
import tools
import models

logger = logging.getLogger(__name__)

class LocalLLMShiftAssistant:
    """Shift scheduling assistant powered by a local LLM via the OpenAI API client,

    with tool calling for inspecting coworker shifts and creating reschedule proposals.
    """

    def __init__(self):
        self.base_url = os.environ.get("OPENAI_BASE_URL", settings.local_llm_base_url)
        self.api_key = os.environ.get("OPENAI_API_KEY", settings.local_llm_api_key)
        self.model = os.environ.get("LOCAL_LLM_MODEL", settings.local_llm_model)
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=0,
            timeout=1.5
        )

    def extract_entities_fallback(self, text: str) -> Dict[str, Any]:
        """Heuristic entity extractor used when local LLM server is offline."""
        entities = {}
        shift_match = re.search(r'\bshift\s*(?:id|#)?\s*(\d+|[a-f0-9\-]{36})\b', text, re.IGNORECASE)
        if shift_match:
            entities["shift_id"] = shift_match.group(1)

        proj_match = re.search(r'\bproject\s*(?:id|#)?\s*(\d+|[a-f0-9\-]{36})\b', text, re.IGNORECASE)
        if proj_match:
            entities["project_id"] = proj_match.group(1)

        length_match = re.search(r'(?:length|duration|for)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:hours|hrs|hr|h)?\b', text, re.IGNORECASE)
        if length_match:
            entities["length"] = float(length_match.group(1))

        iso_match = re.search(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T\s]\d{1,2}:\d{2}(?::\d{2})?)?)\b', text)
        if iso_match:
            entities["date_str"] = iso_match.group(1)

        return entities

    def chat(
        self,
        message: str,
        db: Session,
        current_user: models.Worker,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Chat with local LLM using OpenAI API with tool calling for proposals."""
        system_prompt = (
            f"You are ShiftBridge Assistant, an AI shift scheduling assistant.\n"
            f"Current authenticated worker: ID={current_user.id}, Email={current_user.email}, Name={current_user.name}.\n"
            f"Reference timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            "You have access to the following tools:\n"
            "1. `get_other_workers_shifts`: view coworker shifts.\n"
            "2. `get_my_shifts`: view current user shifts.\n"
            "3. `create_reschedule_proposal`: create a new reschedule proposal record for a shift.\n\n"
            "Rules:\n"
            "- Always call `create_reschedule_proposal` when the user wants to propose rescheduling a shift.\n"
            "- Provide helpful and clear responses."
        )
        print(system_prompt)

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for turn in chat_history:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            import httpx
            request_timeout = httpx.Timeout(215.0, connect=3.0)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools.OPENAI_TOOLS,
                tool_choice="auto",
                timeout=request_timeout
            )

            choice = response.choices[0]
            assistant_msg = choice.message
            tools_executed = []
            created_proposal_data = None

            if assistant_msg.tool_calls:
                messages.append(assistant_msg)
                for tool_call in assistant_msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception as e:
                        logger.info("Local LLM API unavailable (%s); using resilient local engine fallback.", str(e))
                        fn_args = {}

                    tool_result = tools.execute_tool_by_name(
                        tool_name=fn_name,
                        args=fn_args,
                        db=db,
                        current_user_id=current_user.id
                    )

                    tools_executed.append({
                        "tool": fn_name,
                        "arguments": fn_args,
                        "result": tool_result
                    })
                    print('tool_result',tool_result)

                    if fn_name == "create_reschedule_proposal" and tool_result.get("success"):
                        created_proposal_data = tool_result.get("proposal")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=request_timeout
                )
                final_reply = second_response.choices[0].message.content or ""
            else:
                final_reply = assistant_msg.content or ""

            return {
                "reply": final_reply,
                "tools_used": tools_executed,
                "created_proposal": created_proposal_data
            }

        except Exception as e:
            logger.info("Local LLM API unavailable (%s); using resilient local engine fallback.", str(e))
            return {
                "reply": "Error",
                "tools_used": [],
                "created_proposal": None
            }


ai_engine = LocalLLMShiftAssistant()