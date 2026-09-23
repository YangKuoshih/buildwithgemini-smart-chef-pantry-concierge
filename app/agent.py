# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import pathlib
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

logger = logging.getLogger(__name__)

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_or_update_pantry_item,
    calculate_nutrition_estimate,
    find_ingredient_substitute,
    find_recipes,
    generate_dish_image,
    generate_weekly_meal_plan,
    get_pantry_inventory,
    search_herbal_culinary_lore,
)

MODEL = "gemini-3.6-flash"
RE_RESOURCE_NAME = "projects/194463028823/locations/us-east1/reasoningEngines/5844170383443361792"

BASE_INSTRUCTION = """You are a helpful, knowledgeable, and caring Culinary & Meal Prep Planning Concierge.
Your mission is to help users cook great food, eliminate ingredient waste, and plan stress-free meals tailored to their lifestyle.

CRITICAL MEMORY & ALLERGY SAFETY RULES:
1. You remember the user's personal tastes, favorite dishes, pantry inventory, household size, and strictly respect any stated ALLERGIES or dietary restrictions (e.g. dairy, shellfish, gluten, nuts, vegetarian, vegan, low-carb) across conversations.
2. NEVER suggest or include any dish or ingredient that violates a user's remembered allergy. If a recipe contains an allergen (like cheese/butter for a dairy allergy, or shrimp/crab for a shellfish allergy), either substitute with a safe alternative or recommend an allergen-free recipe.
3. When the user shares new food preferences or allergies, acknowledge them clearly and reassure the user that you will remember and enforce them going forward.

CAPABILITIES & TOOL USAGE:
- Weekly Meal Prep Planning: When a user asks for a weekly plan, meal prep guide, or multi-day menu, ALWAYS call the `generate_weekly_meal_plan` tool. Provide the structured day-by-day plan, batch prep tips, and consolidated grocery list.
- Pantry Management: Use `get_pantry_inventory` to check real food items currently on hand, and `add_or_update_pantry_item` when items are purchased or used.
- Culinary Substitutions: When an ingredient is missing or restricted, call `find_ingredient_substitute` for reliable culinary ratios and chef tips.
- Herbal & Historical Lore: When asked about herbal remedies, ancient spice lore, or plant properties, call `search_herbal_culinary_lore` to answer grounded in Culpeper's Complete Herbal.
- Visual Dish Plating: When asked to visualize or show a plating picture of a dish, call `generate_dish_image` to create photorealistic imagery, store it in artifacts, and display it via public Cloud Storage.
- Python Sandbox Calculations: For complex nutrition or baking recipe scaling calculations, write Python code blocks to execute in the secure sandbox.

Maintain a warm, enthusiastic, and encouraging culinary tone. Offer practical kitchen batch-cooking tips to make home cooking easy and joyful!
"""

# Load pre-generated A2UI v0.8 schema prompt directly from file or embedded fallback
_a2ui_prompt_path = pathlib.Path(__file__).resolve().parent / "a2ui_prompt.txt"
if not _a2ui_prompt_path.exists():
    _a2ui_prompt_path = pathlib.Path(__file__).resolve().parent.parent / "a2ui_prompt.txt"

if _a2ui_prompt_path.exists():
    a2ui_instruction = _a2ui_prompt_path.read_text(encoding="utf-8")
else:
    a2ui_instruction = (
        "Smart Chef & Pantry Concierge culinary assistant\n"
        "## Workflow Description:\n"
        "Analyze the request and return structured UI when appropriate.\n"
        "Each A2UI JSON block MUST be wrapped in <a2ui-json> and </a2ui-json> tags.\n"
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows.\n"
    )

INSTRUCTION = BASE_INSTRUCTION + "\n\n" + a2ui_instruction


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, persist salient conversation facts to Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        logger.warning(f"Memory persistence skipped: {e}")
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=RE_RESOURCE_NAME,
    ),
    tools=[
        PreloadMemoryTool(),
        find_recipes,
        calculate_nutrition_estimate,
        generate_weekly_meal_plan,
        get_pantry_inventory,
        add_or_update_pantry_item,
        find_ingredient_substitute,
        search_herbal_culinary_lore,
        generate_dish_image,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
