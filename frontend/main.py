"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
)
try:
    from a2a.types import TransportProtocol
except ImportError:
    try:
        from a2a.compat.v0_3.types import TransportProtocol
    except ImportError:
        from a2a.utils import TransportProtocol
try:
    from a2a.types import FilePart, TextPart
except ImportError:
    FilePart = type("FilePart", (), {})
    TextPart = type("TextPart", (), {})
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/194463028823/locations/us-east1/reasoningEngines/7433941051905146880",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

FIRESTORE_PROJECT = "qwiklabs-gcp-04-0b819a9381db"

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _text_to_a2ui(text: str) -> dict | None:
    """If text contains a structured recipe, convert it into an A2UI v0.8 message with hero image, portioned ingredients, and step-by-step instructions."""
    lower = text.lower()
    if not ("ingredient" in lower and ("instruction" in lower or "step" in lower or "direction" in lower)):
        return None
    if "7-day" in lower or "meal prep plan" in lower or "grocery list" in lower or "meal prep schedule" in lower:
        return None

    # Parse recipe title
    title_match = re.search(r"^#{1,3}\s*(?:🥗|🍳|🍽️|✨)?\s*(?:\*\*)?(?:Featured Recipe:\s*)?([^\n*#]+)(?:\*\*)?", text, re.M)
    title = title_match.group(1).strip() if title_match else "Chef's Featured Recipe"
    if title.lower() in ("overview", "ingredients", "instructions", "recipe"):
        alt_match = re.search(r"(?:for the\s+|recipe:\s*)\*\*([^*]+)\*\*", text, re.I)
        if alt_match:
            title = alt_match.group(1).strip()

    # Parse prep time / calories
    time_match = re.search(r"Prep Time:\s*([^\n*|]+)", text, re.I)
    prep_time = f"⏱️ {time_match.group(1).strip()}" if time_match else "⏱️ 15 mins"

    diff_match = re.search(r"Difficulty(?: Level)?:\s*([^\n*|]+)", text, re.I)
    diff = f"⭐ {diff_match.group(1).strip()}" if diff_match else "⭐ Easy"

    cal_match = re.search(r"(\d+)\s*Calories", text, re.I)
    cals = f"🔥 {cal_match.group(1)} kcal" if cal_match else ""

    prot_match = re.search(r"(\d+g)\s*Protein", text, re.I)
    prot = f"💪 {prot_match.group(1)} protein" if prot_match else ""

    # Parse ingredients and instructions
    ingredients = []
    instructions = []
    in_ingredients = False
    in_instructions = False

    for line in text.splitlines():
        line_clean = line.strip()
        lower_l = line_clean.lower()
        if "ingredients" in lower_l and ("breakdown" in lower_l or line_clean.startswith("#") or line_clean.endswith(":")):
            in_ingredients = True
            in_instructions = False
            continue
        elif ("instructions" in lower_l or "step-by-step" in lower_l or "directions" in lower_l) and (line_clean.startswith("#") or line_clean.endswith(":")):
            in_ingredients = False
            in_instructions = True
            continue
        elif line_clean.startswith("###") or line_clean.startswith("---") or "quick pantry ideas" in lower_l or "culinary tip" in lower_l or "chef's tip" in lower_l:
            in_ingredients = False
            in_instructions = False

        if in_ingredients:
            if line_clean.startswith(("*", "-", "•")):
                item = line_clean.lstrip("*-• ").strip()
                if not item.endswith(":") and "ingredients needed" not in item.lower() and "matched ingredients" not in item.lower():
                    ingredients.append(item)
        elif in_instructions:
            if re.match(r"^\d+\.", line_clean):
                step = re.sub(r"^\d+\.\s*", "", line_clean).strip()
                instructions.append(step)

    if not ingredients and not instructions:
        return None

    # Construct A2UI v0.8 surfaceUpdate
    surface_id = f"recipe_{uuid.uuid4().hex[:8]}"
    comps = []
    col_children = []

    # 0. Check for Hero Image URL in text
    img_match = re.search(r"(https://storage\.googleapis\.com/[^\s\"\')]+\.(?:jpg|jpeg|png)|https://images\.unsplash\.com/[^\s\"\')]+)", text, re.I)
    if img_match:
        img_id = f"hero_img_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": img_id,
            "component": {
                "Image": {
                    "url": {"literalString": img_match.group(1)},
                    "altText": {"literalString": title},
                    "usageHint": "header",
                    "fit": "cover"
                }
            }
        })
        col_children.append(img_id)

    # 1. Title
    t_id = f"title_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": t_id,
        "component": {"Text": {"text": {"literalString": f"🍳 {title}"}, "usageHint": "h1"}}
    })
    col_children.append(t_id)

    # 2. Meta row
    meta_items = [prep_time, diff, cals, prot]
    meta_items = [m for m in meta_items if m]
    if meta_items:
        row_id = f"meta_{uuid.uuid4().hex[:4]}"
        row_kids = []
        for idx, m in enumerate(meta_items):
            mid = f"m_{idx}_{uuid.uuid4().hex[:4]}"
            comps.append({
                "id": mid,
                "component": {"Text": {"text": {"literalString": m}, "usageHint": "caption"}}
            })
            row_kids.append(mid)
        comps.append({
            "id": row_id,
            "component": {"Row": {"children": {"explicitList": row_kids}}}
        })
        col_children.append(row_id)

    # 3. Divider
    div1_id = f"div_{uuid.uuid4().hex[:4]}"
    comps.append({"id": div1_id, "component": {"Divider": {}}})
    col_children.append(div1_id)

    # 4. Ingredients section with exact portions
    if ingredients:
        ing_head_id = f"ing_h_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": ing_head_id,
            "component": {"Text": {"text": {"literalString": "🛒 Portioned Ingredients"}, "usageHint": "h3"}}
        })
        col_children.append(ing_head_id)

        ing_kids = []
        for idx, ing in enumerate(ingredients):
            iid = f"ing_{idx}_{uuid.uuid4().hex[:4]}"
            clean_ing = re.sub(r"^\s*[*•-]\s*", "", ing)
            clean_ing = re.sub(r"\*+", "", clean_ing).strip()
            comps.append({
                "id": iid,
                "component": {"Text": {"text": {"literalString": f"• {clean_ing}"}, "usageHint": "body"}}
            })
            ing_kids.append(iid)

        list1_id = f"ing_list_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": list1_id,
            "component": {"List": {"children": {"explicitList": ing_kids}}}
        })
        col_children.append(list1_id)

    # 5. Instructions section with step badges
    if instructions:
        div2_id = f"div2_{uuid.uuid4().hex[:4]}"
        comps.append({"id": div2_id, "component": {"Divider": {}}})
        col_children.append(div2_id)

        inst_head_id = f"inst_h_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": inst_head_id,
            "component": {"Text": {"text": {"literalString": "👨‍🍳 Step-by-Step Instructions"}, "usageHint": "h3"}}
        })
        col_children.append(inst_head_id)

        inst_kids = []
        for idx, inst in enumerate(instructions):
            sid = f"step_{idx}_{uuid.uuid4().hex[:4]}"
            clean_inst = re.sub(r"^\s*\d+\.\s*", "", inst)
            clean_inst = re.sub(r"\*+", "", clean_inst).strip()
            comps.append({
                "id": sid,
                "component": {"Text": {"text": {"literalString": f"{idx+1}. {clean_inst}"}, "usageHint": "body"}}
            })
            inst_kids.append(sid)

        list2_id = f"inst_list_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": list2_id,
            "component": {"List": {"children": {"explicitList": inst_kids}}}
        })
        col_children.append(list2_id)

    # Root Column
    col_id = f"col_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": col_id,
        "component": {"Column": {"children": {"explicitList": col_children}}}
    })

    # Root Card
    root_card_id = f"card_{uuid.uuid4().hex[:4]}"
    comps.insert(0, {
        "id": root_card_id,
        "component": {"Card": {"child": col_id}}
    })

    return {
        "surfaceUpdate": {
            "surfaceId": surface_id,
            "components": comps
        }
    }


def _suggestions_to_a2ui(text: str) -> dict | None:
    """If text contains dish suggestions, convert it into a structured A2UI v0.8 message."""
    lower = text.lower()
    has_ing = bool(re.search(r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:🛒\s*)?ingredients", lower))
    has_inst = bool(re.search(r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:👨‍🍳\s*)?(?:step-by-step\s+)?(?:instructions|directions)", lower))
    has_bullets = any(line.strip().startswith(("• ", "* ", "- ")) for line in text.splitlines())
    has_numbered_steps = any(re.match(r"^\d+\.\s+(?:Prep|Cook|Heat|Sauté|Mix|Bake|Serve|Simmer|Boil|Chop|Season|Toss|Combine)", line.strip(), re.I) for line in text.splitlines())
    if (has_ing and has_bullets) or has_numbered_steps:
        return None

    lines = text.splitlines()
    dish_items = []
    current_dish = None

    for line in lines:
        l_str = line.strip()
        # Match numbered dish header: e.g. "1. Classic Chicken Fried Rice" or "### 1. Dish"
        m = re.match(r"^(?:#{1,3}\s*)?(?:\d+\.|\*|\-)\s*(?:\*\*)?(?:[🍽️🥗🍲🍳🥪🥘🥩🍛✨]?\s*)([A-Z][^\n*:(]+)(?:\*\*)?", l_str)
        if m and not any(kw in m.group(1).lower() for kw in ("chef", "suggestion", "ingredient", "instruction", "step", "prep", "tip", "grocery", "overview")):
            if current_dish and (current_dish["desc"] or current_dish["meta"]):
                dish_items.append(current_dish)
            current_dish = {"title": m.group(1).strip(), "desc": [], "meta": []}
            continue

        if current_dish:
            if any(k in l_str.lower() for k in ("time:", "difficulty:", "pantry match:", "⏱️", "🟢", "🏷️", "⭐", "uses ")):
                current_dish["meta"].append(l_str)
            elif l_str and not l_str.startswith("#") and not l_str.startswith("---") and "ready to cook" not in l_str.lower():
                current_dish["desc"].append(l_str)

    if current_dish and (current_dish["desc"] or current_dish["meta"]):
        dish_items.append(current_dish)

    if len(dish_items) < 2:
        return None

    surface_id = f"suggestions_{uuid.uuid4().hex[:8]}"
    comps = []
    col_children = []

    # Title
    t_id = f"sug_title_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": t_id,
        "component": {"Text": {"text": {"literalString": "🍽️ Chef's Dish Suggestions"}, "usageHint": "h1"}}
    })
    col_children.append(t_id)

    # Subtitle
    sub_id = f"sug_sub_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": sub_id,
        "component": {"Text": {"text": {"literalString": "Personalized recipe ideas based on your available ingredients:"}, "usageHint": "caption"}}
    })
    col_children.append(sub_id)

    div_id = f"sug_div_{uuid.uuid4().hex[:4]}"
    comps.append({"id": div_id, "component": {"Divider": {}}})
    col_children.append(div_id)

    for idx, d in enumerate(dish_items):
        dt_id = f"dish_t_{idx}_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": dt_id,
            "component": {"Text": {"text": {"literalString": f"### {idx+1}. {d['title']}"}, "usageHint": "h2"}}
        })
        col_children.append(dt_id)

        if d["desc"]:
            dd_id = f"dish_d_{idx}_{uuid.uuid4().hex[:4]}"
            comps.append({
                "id": dd_id,
                "component": {"Text": {"text": {"literalString": " ".join(d['desc'])}, "usageHint": "body"}}
            })
            col_children.append(dd_id)

        if d["meta"]:
            dm_id = f"dish_m_{idx}_{uuid.uuid4().hex[:4]}"
            comps.append({
                "id": dm_id,
                "component": {"Text": {"text": {"literalString": " | ".join(d['meta'])}, "usageHint": "caption"}}
            })
            col_children.append(dm_id)

        sep_id = f"dish_sep_{idx}_{uuid.uuid4().hex[:4]}"
        comps.append({"id": sep_id, "component": {"Divider": {}}})
        col_children.append(sep_id)

    # Closing CTA
    cta_id = f"sug_cta_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": cta_id,
        "component": {"Text": {"text": {"literalString": "👉 Ready to cook? Ask me: \"Give me the recipe for [Dish Name]\" to see exact portioned ingredients, step-by-step instructions, and a photo of the finished dish!"}, "usageHint": "body"}}
    })
    col_children.append(cta_id)

    col_id = f"col_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": col_id,
        "component": {"Column": {"children": {"explicitList": col_children}}}
    })

    root_card_id = f"card_{uuid.uuid4().hex[:4]}"
    comps.insert(0, {
        "id": root_card_id,
        "component": {"Card": {"child": col_id}}
    })

    return {
        "surfaceUpdate": {
            "surfaceId": surface_id,
            "components": comps
        }
    }


def _bound_str(val):
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("literalString", "") or val.get("path", "") or ""
    return str(val) if val is not None else ""


def _extract_text_from_a2ui(payload: dict) -> str:
    texts = []
    su = payload.get("surfaceUpdate") or (payload.get("components") and payload)
    if isinstance(su, dict):
        for c in su.get("components", []):
            comp = c.get("component", {}) if isinstance(c, dict) else {}
            if "Text" in comp:
                t = _bound_str(comp["Text"].get("text"))
                if t:
                    texts.append(t)
    return "\n\n".join(texts)


def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    has_a2ui = False

    for p in parts:
        root = getattr(p, "root", p)
        # Direct A2UI data part
        if getattr(root, "data", None) is not None:
            raw_data = root.data
            inner = raw_data.get("data") if isinstance(raw_data, dict) else None
            meta = (raw_data.get("metadata") if isinstance(raw_data, dict) else None) or getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME or (isinstance(inner, dict) and any(k in inner for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate"))):
                payload = inner if (isinstance(inner, dict) and any(k in inner for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate"))) else raw_data
                raw_text = _extract_text_from_a2ui(payload)
                out.append({"kind": "a2ui", "data": payload, "rawText": raw_text})
                has_a2ui = True
                continue
            elif isinstance(raw_data, dict) and any(k in raw_data for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate")):
                raw_text = _extract_text_from_a2ui(raw_data)
                out.append({"kind": "a2ui", "data": raw_data, "rawText": raw_text})
                has_a2ui = True
                continue

        text = getattr(root, "text", None)
        if text:
            # Check for embedded <a2a_datapart_json>
            if "<a2a_datapart_json>" in text:
                matches = re.findall(r"<a2a_datapart_json>(.*?)</a2a_datapart_json>", text, re.DOTALL)
                for m in matches:
                    try:
                        parsed = json.loads(m.strip())
                        data = parsed.get("data")
                        if data:
                            out.append({"kind": "a2ui", "data": data})
                            has_a2ui = True
                    except Exception:
                        pass
                text = re.sub(r"<a2a_datapart_json>.*?</a2a_datapart_json>", "", text, flags=re.DOTALL).strip()

            # Check for embedded <a2ui-json>
            if "<a2ui-json>" in text:
                matches = re.findall(r"<a2ui-json>(.*?)</a2ui-json>", text, re.DOTALL)
                for m in matches:
                    try:
                        parsed = json.loads(m.strip())
                        if isinstance(parsed, list):
                            for item in parsed:
                                out.append({"kind": "a2ui", "data": item})
                                has_a2ui = True
                        elif isinstance(parsed, dict):
                            out.append({"kind": "a2ui", "data": parsed})
                            has_a2ui = True
                    except Exception:
                        pass
                text = re.sub(r"<a2ui-json>.*?</a2ui-json>", "", text, flags=re.DOTALL).strip()

            if text.strip():
                # If no A2UI was explicitly emitted, check if this text is a recipe we can convert to A2UI
                if not has_a2ui:
                    recipe_a2ui = _text_to_a2ui(text)
                    if recipe_a2ui:
                        recipe_pattern = r"(?:---\s*)?###\s*(?:🥗|🍳|🍽️|✨)?\s*(?:\*\*)?(?:Featured Recipe:\s*)?([^\n*]+)(?:\*\*)?.*?(?=(?:\n---\s*\n\s*###\s+[^\n#]+|\n###\s+[^\n#]+|\Z))"
                        rec_match = re.search(recipe_pattern, text, re.DOTALL | re.I)
                        if rec_match:
                            intro = text[:rec_match.start()].strip()
                            recipe_body = text[rec_match.start():rec_match.end()].strip()
                            remainder = text[rec_match.end():].strip()
                            remainder = re.sub(r"^\s*---\s*", "", remainder).strip()
                            if intro:
                                out.append({"kind": "text", "text": intro})
                            out.append({"kind": "a2ui", "data": recipe_a2ui, "rawText": recipe_body})
                            if remainder:
                                out.append({"kind": "text", "text": remainder})
                            has_a2ui = True
                            continue
                        else:
                            out.append({"kind": "a2ui", "data": recipe_a2ui, "rawText": text})
                            has_a2ui = True
                            continue
                    else:
                        suggestions_a2ui = _suggestions_to_a2ui(text)
                        if suggestions_a2ui:
                            out.append({"kind": "a2ui", "data": suggestions_a2ui, "rawText": text})
                            has_a2ui = True
                            continue

                out.append({"kind": "text", "text": text})
            continue

        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})

    return out


@app.get("/api/pantry")
async def get_pantry():
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT)
        docs = db.collection("pantry_inventory").stream()
        items = []
        for d in docs:
            data = d.to_dict()
            items.append({
                "id": d.id,
                "item_name": data.get("item_name", d.id),
                "quantity": data.get("quantity", 0),
                "unit": data.get("unit", ""),
                "category": data.get("category", "General"),
                "days_until_expiration": data.get("days_until_expiration", 14),
            })
        return JSONResponse({"items": items})
    except Exception as e:
        return JSONResponse({"items": [], "error": str(e)})


@app.post("/api/reset")
async def reset_session(req: Request = None):
    global _contexts
    if req is not None:
        try:
            body = await req.json()
            uid = body.get("user_id")
            if uid and uid in _contexts:
                _contexts.pop(uid, None)
                return JSONResponse({"status": "reset", "message": f"Session {uid} reset successfully"})
        except Exception:
            pass
    _contexts.clear()
    return JSONResponse({"status": "reset", "message": "All sessions reset successfully"})


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        artifact_parts: list[dict] = []
        latest_status_message = None

        try:
            async for event in a2a_client.send_message(msg):
                if not isinstance(event, tuple):
                    continue
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    artifact_parts.extend(_extract_parts(update.artifact.parts))
                elif hasattr(update, "status") and getattr(update.status, "message", None):
                    status_msg = update.status.message
                    if getattr(status_msg, "parts", None):
                        latest_status_message = status_msg
        except Exception as e:
            # If sending fails on existing context, clear context so user can retry cleanly
            _contexts.pop(user_id, None)
            return JSONResponse({"parts": [{"kind": "text", "text": f"⚠️ Communication error: {str(e)}. Session has been refreshed, please try your prompt again."}]})

        # Process artifact parts first
        if artifact_parts:
            parts.extend(artifact_parts)
        elif latest_status_message:
            for p in _extract_parts(latest_status_message.parts):
                if p not in parts:
                    parts.append(p)

        # Fallback to task history if stream didn't yield parts
        if not parts and last_task is not None:
            for h_msg in getattr(last_task, "history", None) or []:
                if getattr(h_msg, "role", None) in (Role.agent, "agent") and getattr(h_msg, "parts", None):
                    for p in _extract_parts(h_msg.parts):
                        if p not in parts:
                            parts.append(p)
            if not parts:
                for artifact in getattr(last_task, "artifacts", None) or []:
                    for p in _extract_parts(artifact.parts):
                        if p not in parts:
                            parts.append(p)

        # Check if the task failed
        task_state = getattr(getattr(last_task, "status", None), "state", None)
        if task_state in ("failed", TaskState.failed):
            _contexts.pop(user_id, None)
            if not parts:
                st_msg = getattr(getattr(last_task, "status", None), "message", None)
                if st_msg and getattr(st_msg, "parts", None):
                    parts.extend(_extract_parts(st_msg.parts))
                if not parts:
                    parts = [{"kind": "text", "text": "👨‍🍳 Chef assistant encountered an issue generating this recipe. Your session has been refreshed—please try your request again."}]

    if not parts:
        parts = [{"kind": "text", "text": "👨‍🍳 Chef assistant is ready! Please try submitting your question again."}]
    return JSONResponse({"parts": parts})


app.mount("/static", StaticFiles(directory="static"), name="static_dir")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
