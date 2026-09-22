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
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/194463028823/locations/us-east1/reasoningEngines/6868176348716728320",
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
    """If text contains a structured recipe, convert it into an A2UI v0.8 message."""
    if not ("ingredient" in text.lower() and ("instruction" in text.lower() or "step" in text.lower() or "direction" in text.lower())):
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
        lower = line_clean.lower()
        if "ingredients" in lower and ("breakdown" in lower or line_clean.startswith("#") or line_clean.endswith(":")):
            in_ingredients = True
            in_instructions = False
            continue
        elif ("instructions" in lower or "step-by-step" in lower or "directions" in lower) and (line_clean.startswith("#") or line_clean.endswith(":")):
            in_ingredients = False
            in_instructions = True
            continue
        elif line_clean.startswith("###") or line_clean.startswith("---") or "quick pantry ideas" in lower or "culinary tip" in lower:
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

    # 1. Title
    t_id = f"title_{uuid.uuid4().hex[:4]}"
    comps.append({
        "id": t_id,
        "component": {"Text": {"text": {"literalString": f"🥗 {title}"}, "usageHint": "h1"}}
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

    # 4. Ingredients section
    if ingredients:
        ing_head_id = f"ing_h_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": ing_head_id,
            "component": {"Text": {"text": {"literalString": "Ingredients"}, "usageHint": "h3"}}
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

    # 5. Instructions section
    if instructions:
        div2_id = f"div2_{uuid.uuid4().hex[:4]}"
        comps.append({"id": div2_id, "component": {"Divider": {}}})
        col_children.append(div2_id)

        inst_head_id = f"inst_h_{uuid.uuid4().hex[:4]}"
        comps.append({
            "id": inst_head_id,
            "component": {"Text": {"text": {"literalString": "Cooking Instructions"}, "usageHint": "h3"}}
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


def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    has_a2ui = False

    for p in parts:
        root = getattr(p, "root", p)
        # Direct A2UI data part
        if getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
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
                            remainder = text[rec_match.end():].strip()
                            remainder = re.sub(r"^\s*---\s*", "", remainder).strip()
                            if intro:
                                out.append({"kind": "text", "text": intro})
                            out.append({"kind": "a2ui", "data": recipe_a2ui})
                            if remainder:
                                out.append({"kind": "text", "text": remainder})
                            has_a2ui = True
                            continue
                        else:
                            out.append({"kind": "a2ui", "data": recipe_a2ui})
                            has_a2ui = True

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
async def reset_session():
    global _contexts
    _contexts.clear()
    return JSONResponse({"status": "reset", "message": "Session reset successfully"})


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
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))
            elif hasattr(update, "status") and getattr(update.status, "message", None):
                status_msg = update.status.message
                if getattr(status_msg, "parts", None):
                    parts.extend(_extract_parts(status_msg.parts))

        if not parts and last_task is not None:
            for h_msg in getattr(last_task, "history", None) or []:
                if getattr(h_msg, "role", None) in (Role.agent, "agent") and getattr(h_msg, "parts", None):
                    parts.extend(_extract_parts(h_msg.parts))
            if not parts:
                for artifact in getattr(last_task, "artifacts", None) or []:
                    parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


app.mount("/static", StaticFiles(directory="static"), name="static_dir")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
