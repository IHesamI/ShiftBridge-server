import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dateutil import parser as date_parser
from openai import OpenAI

from config import settings
import tools
import models

logger = logging.getLogger(__name__)

class LocalLLMShiftAssistant:
    """Shift scheduling assistant powered by a local LLM via the OpenAI API client,

    with tool calling for inspecting coworker shifts and rescheduling user shifts.
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
        shift_match = re.search(r'\bshift\s*(?:id|#)?\s*(\d+)\b', text, re.IGNORECASE)
        if shift_match:
            entities["shift_id"] = int(shift_match.group(1))

        proj_match = re.search(r'\bproject\s*(?:id|#)?\s*(\d+)\b', text, re.IGNORECASE)
        if proj_match:
            entities["project_id"] = int(proj_match.group(1))

        length_match = re.search(r'(?:length|duration|for)\s*(?:of)?\s*(\d+)\s*(?:hours|hrs|hr|h)?\b', text, re.IGNORECASE)
        if length_match:
            entities["length"] = int(length_match.group(1))
        else:
            hours_match = re.search(r'\b(\d+)\s*(?:hours|hrs|hr)\b', text, re.IGNORECASE)
            if hours_match:
                entities["length"] = int(hours_match.group(1))

        iso_match = re.search(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T\s]\d{1,2}:\d{2}(?::\d{2})?)?)\b', text)
        if iso_match:
            entities["date_str"] = iso_match.group(1)
        else:
            lower = text.lower()
            if "tomorrow" in lower:
                time_match = re.search(r'(?:at|@)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', lower)
                h, m = 9, 0
                if time_match:
                    h = int(time_match.group(1))
                    m = int(time_match.group(2)) if time_match.group(2) else 0
                    if time_match.group(3) == "pm" and h < 12:
                        h += 12
                    elif time_match.group(3) == "am" and h == 12:
                        h = 0
                target = (datetime.now() + timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
                entities["date_str"] = target.strftime("%Y-%m-%d %H:%M:%S")

        return entities

    def _fallback_process(
        self,
        message: str,
        db: Session,
        current_user: models.User,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Local fallback when OpenAI API server endpoint is not running."""
        text = message.strip()
        lower_text = text.lower()
        tools_executed = []
        updated_shift_data = None
        entities = self.extract_entities_fallback(text)

        context_text = ""
        if chat_history:
            for turn in chat_history[-3:]:
                context_text += f"{turn.get('role', '')}: {turn.get('content', '')}\n"

        is_other_workers = any(k in lower_text for k in [
            "other worker", "other workers", "coworker", "coworkers", "colleague", "colleagues",
            "other shift", "other shifts", "others shift", "who is working", "team schedule"
        ])
        is_reschedule = any(k in lower_text for k in [
            "reschedule", "change shift", "move shift", "postpone", "switch shift", "change my shift"
        ])
        is_my_shifts = any(k in lower_text for k in [
            "my shift", "my shifts", "my schedule", "when do i work", "what shifts"
        ])

        reply_parts = []

        if is_other_workers:
            proj_id = entities.get("project_id")
            tool_args = {"project_id": proj_id} if proj_id else {}
            res = tools.tool_get_other_workers_shifts(db, current_user.id, project_id=proj_id)
            tools_executed.append({
                "tool": "get_other_workers_shifts",
                "arguments": tool_args,
                "result": res
            })
            shifts = res.get("shifts", [])
            if not shifts:
                reply_parts.append("No shifts scheduled for other workers on this project.")
            else:
                reply_parts.append(f"Here are the scheduled shifts for other workers ({len(shifts)} found):")
                for s in shifts:
                    dt = s['start_date'].replace('T', ' ')
                    reply_parts.append(f"• {s['worker_name']} ({s['worker_email']}): {dt} ({s['length']} hrs) [Shift #{s['shift_id']}]")

        if is_reschedule:
            date_str = entities.get("date_str")
            shift_id = entities.get("shift_id")
            length = entities.get("length")

            if not date_str:
                to_match = re.search(r'(?:to|for|at)\s+([0-9\-\/]{8,10}(?:\s+[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)?)', text, re.IGNORECASE)
                if to_match:
                    date_str = to_match.group(1)

            if not date_str:
                my_shifts_res = tools.tool_get_my_shifts(db, current_user.id)
                tools_executed.append({
                    "tool": "get_my_shifts",
                    "arguments": {},
                    "result": my_shifts_res
                })
                shifts = my_shifts_res.get("shifts", [])
                if not shifts:
                    reply_parts.append("You do not currently have any scheduled shifts to reschedule.")
                else:
                    reply_parts.append("I can help you reschedule your shift. What new date and time would you like to move it to?")
                    reply_parts.append("Here are your current shifts:")
                    for s in shifts:
                        reply_parts.append(f"• Shift #{s['shift_id']} on {s['start_date'].replace('T', ' ')} ({s['length']} hrs)")
            else:
                tool_args = {"shift_id": shift_id, "new_start_date": date_str, "new_length": length}
                tool_res = tools.tool_reschedule_shift(
                    db=db,
                    current_user_id=current_user.id,
                    new_start_date=date_str,
                    shift_id=shift_id,
                    new_length=length
                )
                tools_executed.append({
                    "tool": "reschedule_shift",
                    "arguments": tool_args,
                    "result": tool_res
                })
                if tool_res.get("success"):
                    updated_shift_data = tool_res.get("shift")
                    sh = updated_shift_data
                    reply_parts.append(
                        f"✅ Shift #{sh['shift_id']} has been successfully rescheduled to {sh['new_start_date'].replace('T', ' ')} ({sh['new_length']} hours)."
                    )
                else:
                    reply_parts.append(f"❌ Could not reschedule shift: {tool_res.get('error')}")

        elif is_my_shifts and not is_other_workers:
            my_shifts_res = tools.tool_get_my_shifts(db, current_user.id)
            tools_executed.append({"tool": "get_my_shifts", "arguments": {}, "result": my_shifts_res})
            shifts = my_shifts_res.get("shifts", [])
            if not shifts:
                reply_parts.append("You currently have no scheduled shifts.")
            else:
                reply_parts.append(f"You have {len(shifts)} scheduled shift(s):")
                for s in shifts:
                    reply_parts.append(f"• Shift #{s['shift_id']}: {s['start_date'].replace('T', ' ')} ({s['length']} hrs)")

        if not reply_parts:
            reply_parts.append(
                f"Hello {current_user.full_name or current_user.email}! I am your AI Shift Assistant (Local LLM via OpenAI API).\n"
                "You can chat with me to inspect other workers' shifts, view your schedule, or reschedule your shifts."
            )

        return {
            "reply": "\n".join(reply_parts),
            "tools_used": tools_executed,
            "updated_shift": updated_shift_data
        }

    def chat(
        self,
        message: str,
        db: Session,
        current_user: models.User,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Chat with the local LLM model using the OpenAI API with function/tool calling."""
        system_prompt = (
            f"You are ShiftBridge Assistant, an AI shift scheduling assistant for local workers.\n"
            f"Current authenticated worker: ID={current_user.id}, Email={current_user.email}, Name={current_user.full_name or 'N/A'}.\n"
            f"Reference timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
            "You have access to the following tools via OpenAI function calling:\n"
            "1. `get_other_workers_shifts`: to view shifts of coworkers on projects.\n"
            "2. `get_my_shifts`: to view shifts belonging to the current user.\n"
            "3. `reschedule_shift`: to reschedule an existing shift for the current user to a new date/time.\n\n"
            "Rules:\n"
            "- Always call the appropriate tool when asked about coworker shifts, user shifts, or rescheduling.\n"
            "- If the user wants to reschedule but hasn't given a new date/time, call `get_my_shifts` to display their shifts and ask for the new date/time.\n"
            "- Provide helpful, polite, and clear responses."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for turn in chat_history:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            import httpx
            # Allow up to 215s for local model generation, with a fast 3s connection check if server is down
            request_timeout = httpx.Timeout(215.0, connect=3.0)

            # Call local LLM via OpenAI API
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
            updated_shift_data = None

            # Handle tool calls if returned by local LLM
            if assistant_msg.tool_calls:
                # Add assistant message with tool calls to conversation
                messages.append(assistant_msg)
                for tool_call in assistant_msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
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

                    if fn_name == "reschedule_shift" and tool_result.get("success"):
                        updated_shift_data = tool_result.get("shift")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                # Second turn: send tool execution outputs back to local LLM for final response
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
                "updated_shift": updated_shift_data
            }

        except Exception as e:
            print(str(e))
            logger.info("Local LLM API unavailable (%s); using resilient local engine fallback.", str(e))
            return self._fallback_process(
                message=message,
                db=db,
                current_user=current_user,
                chat_history=chat_history
            )


# Singleton instance of local LLM shift assistant
ai_engine = LocalLLMShiftAssistant()
