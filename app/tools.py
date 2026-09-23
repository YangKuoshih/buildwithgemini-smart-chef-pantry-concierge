"""Custom function tools for the Recipe & Meal Suggestion Agent."""

import uuid
from typing import Any, Dict, List, Optional
from google.cloud import firestore, storage
from google.genai import types
from google.adk.tools import ToolContext

import os

# Dynamically resolve project ID and bucket name from environment (fallback to defaults)
GOOGLE_CLOUD_PROJECT = (
    os.environ.get("GOOGLE_CLOUD_PROJECT")
    or os.environ.get("PROJECT_ID")
    or "qwiklabs-gcp-04-0b819a9381db"
)
FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", GOOGLE_CLOUD_PROJECT)
IMAGE_BUCKET_NAME = os.environ.get(
    "IMAGE_BUCKET_NAME", f"smart-chef-pantry-{GOOGLE_CLOUD_PROJECT}"
)
RAG_CORPUS_NAME = os.environ.get(
    "RAG_CORPUS_NAME",
    "projects/194463028823/locations/us-central1/ragCorpora/4287629155396222976",
)

RECIPE_DATABASE = [
    # Breakfasts
    {
        "name": "Spinach & Cheddar Omelet",
        "description": "Fluffy folded eggs filled with fresh baby spinach and sharp cheddar cheese.",
        "meal_type": ["breakfast"],
        "ingredients": ["eggs", "spinach", "cheddar cheese", "butter", "black pepper"],
        "dietary": ["vegetarian", "gluten-free", "low-carb"],
        "prep_time_minutes": 10,
        "difficulty": "Easy",
        "instructions": [
            "Whisk eggs with a splash of water, salt, and pepper.",
            "Melt butter in a non-stick pan over medium heat.",
            "Pour eggs into the pan and let set slightly, then fold in spinach and cheddar cheese.",
            "Fold omelet in half once cheese starts melting, cook for 1 minute more and serve."
        ],
        "nutrition_per_serving": {
            "calories": 290,
            "protein_g": 21,
            "carbs_g": 3,
            "fat_g": 22
        }
    },
    {
        "name": "Overnight Berry Chia Oats",
        "description": "Creamy rolled oats soaked in almond milk with chia seeds, maple syrup, and fresh berries.",
        "meal_type": ["breakfast"],
        "ingredients": ["rolled oats", "chia seeds", "almond milk", "maple syrup", "berries"],
        "dietary": ["vegan", "vegetarian", "dairy-free"],
        "prep_time_minutes": 5,
        "difficulty": "Easy",
        "instructions": [
            "Combine rolled oats, chia seeds, and almond milk in a mason jar.",
            "Stir in maple syrup and refrigerate overnight (at least 6 hours).",
            "Top with fresh berries and crushed almonds before serving."
        ],
        "nutrition_per_serving": {
            "calories": 310,
            "protein_g": 10,
            "carbs_g": 52,
            "fat_g": 8
        }
    },
    {
        "name": "Avocado & Poached Egg Toast",
        "description": "Toasted sourdough bread topped with creamy mashed avocado, soft-poached egg, and chili flakes.",
        "meal_type": ["breakfast"],
        "ingredients": ["sourdough bread", "avocado", "eggs", "lemon", "red pepper flakes"],
        "dietary": ["vegetarian", "dairy-free"],
        "prep_time_minutes": 12,
        "difficulty": "Easy",
        "instructions": [
            "Toast sourdough bread slices until golden crisp.",
            "Mash ripe avocado with lemon juice, salt, and black pepper.",
            "Poach eggs in gently simmering water for 3-4 minutes.",
            "Spread avocado over toast, top with poached egg, and sprinkle red pepper flakes."
        ],
        "nutrition_per_serving": {
            "calories": 330,
            "protein_g": 14,
            "carbs_g": 28,
            "fat_g": 19
        }
    },
    {
        "name": "Greek Yogurt Berry Crunch Bowl",
        "description": "Thick Greek yogurt topped with crunchy granola, mixed berries, and a drizzle of honey.",
        "meal_type": ["breakfast"],
        "ingredients": ["greek yogurt", "granola", "mixed berries", "honey"],
        "dietary": ["vegetarian", "gluten-free"],
        "prep_time_minutes": 5,
        "difficulty": "Easy",
        "instructions": [
            "Spoon Greek yogurt into a serving bowl.",
            "Top with fresh mixed berries and toasted granola.",
            "Drizzle golden honey over top and serve immediately."
        ],
        "nutrition_per_serving": {
            "calories": 280,
            "protein_g": 18,
            "carbs_g": 36,
            "fat_g": 6
        }
    },
    {
        "name": "Sweet Potato & Black Bean Hash",
        "description": "Spiced diced sweet potatoes skillet-fried with black beans, bell peppers, and cilantro.",
        "meal_type": ["breakfast"],
        "ingredients": ["sweet potatoes", "black beans", "bell pepper", "olive oil", "cumin"],
        "dietary": ["vegan", "vegetarian", "gluten-free", "dairy-free"],
        "prep_time_minutes": 20,
        "difficulty": "Easy",
        "instructions": [
            "Dice sweet potatoes into small cubes and microwave for 3 minutes to soften.",
            "Sauté sweet potatoes and diced bell peppers in olive oil until crispy.",
            "Stir in black beans, cumin, salt, and smoked paprika for 3 minutes.",
            "Garnish with chopped cilantro and lime wedge."
        ],
        "nutrition_per_serving": {
            "calories": 290,
            "protein_g": 8,
            "carbs_g": 54,
            "fat_g": 6
        }
    },
    {
        "name": "Smoked Salmon & Scrambled Eggs",
        "description": "Soft gently scrambled eggs folded with smoked salmon ribbon and fresh chives.",
        "meal_type": ["breakfast"],
        "ingredients": ["eggs", "smoked salmon", "butter", "chives", "black pepper"],
        "dietary": ["gluten-free", "low-carb"],
        "prep_time_minutes": 10,
        "difficulty": "Easy",
        "instructions": [
            "Gently whisk eggs with a pinch of black pepper.",
            "Melt butter in a skillet over low heat and scramble eggs slowly until soft curd forms.",
            "Fold in smoked salmon ribbons and fresh chopped chives right before taking off heat."
        ],
        "nutrition_per_serving": {
            "calories": 310,
            "protein_g": 26,
            "carbs_g": 2,
            "fat_g": 22
        }
    },
    {
        "name": "Banana Almond Protein Smoothie",
        "description": "Energizing blended smoothie with ripe banana, almond milk, plant protein, and flaxseeds.",
        "meal_type": ["breakfast"],
        "ingredients": ["banana", "almond milk", "almond butter", "flaxseeds", "cinnamon"],
        "dietary": ["vegan", "vegetarian", "gluten-free", "dairy-free"],
        "prep_time_minutes": 5,
        "difficulty": "Easy",
        "instructions": [
            "Place sliced banana, almond butter, flaxseeds, and almond milk into a blender.",
            "Blend on high speed for 60 seconds until smooth and creamy.",
            "Dust with ground cinnamon and enjoy chilled."
        ],
        "nutrition_per_serving": {
            "calories": 320,
            "protein_g": 12,
            "carbs_g": 44,
            "fat_g": 13
        }
    },

    # Lunches
    {
        "name": "Mediterranean Chickpea & Cucumber Salad",
        "description": "Crisp cucumbers, chickpeas, and ripe tomatoes tossed in lemon olive oil vinaigrette.",
        "meal_type": ["lunch"],
        "ingredients": ["chickpeas", "cucumber", "tomatoes", "olive oil", "lemon"],
        "dietary": ["vegan", "vegetarian", "gluten-free", "dairy-free"],
        "prep_time_minutes": 15,
        "difficulty": "Easy",
        "instructions": [
            "Rinse and drain canned chickpeas.",
            "Dice cucumbers and cherry tomatoes.",
            "Whisk together extra virgin olive oil, lemon juice, salt, and pepper.",
            "Toss chickpeas and vegetables with dressing and chill before serving."
        ],
        "nutrition_per_serving": {
            "calories": 250,
            "protein_g": 9,
            "carbs_g": 32,
            "fat_g": 10
        }
    },
    {
        "name": "Quinoa Power Bowl with Roasted Veggies",
        "description": "Fluffy quinoa topped with roasted sweet potatoes, kale, chickpeas, and tahini drizzle.",
        "meal_type": ["lunch"],
        "ingredients": ["quinoa", "sweet potatoes", "kale", "chickpeas", "tahini", "olive oil"],
        "dietary": ["vegan", "vegetarian", "gluten-free", "dairy-free"],
        "prep_time_minutes": 25,
        "difficulty": "Easy",
        "instructions": [
            "Cook quinoa according to package directions.",
            "Roast cubed sweet potatoes and chickpeas at 400°F (200°C) for 20 minutes.",
            "Massage kale with a drop of olive oil and arrange in bowls with quinoa and roasted veggies.",
            "Drizzle with lemon tahini dressing."
        ],
        "nutrition_per_serving": {
            "calories": 380,
            "protein_g": 14,
            "carbs_g": 58,
            "fat_g": 12
        }
    },
    {
        "name": "Turkey Bacon & Avocado Lettuce Wraps",
        "description": "Crisp romaine hearts wrapped around lean sliced turkey, ripe avocado, and tomato slices.",
        "meal_type": ["lunch"],
        "ingredients": ["turkey breast", "avocado", "romaine lettuce", "tomatoes", "dijon mustard"],
        "dietary": ["gluten-free", "low-carb", "dairy-free"],
        "prep_time_minutes": 10,
        "difficulty": "Easy",
        "instructions": [
            "Wash and dry sturdy romaine lettuce leaves.",
            "Layer sliced roasted turkey breast and avocado slices into each lettuce boat.",
            "Add diced tomatoes and a drizzle of dijon mustard.",
            "Roll up or enjoy open-faced."
        ],
        "nutrition_per_serving": {
            "calories": 280,
            "protein_g": 26,
            "carbs_g": 8,
            "fat_g": 16
        }
    },
    {
        "name": "Lemon Herb Grilled Chicken Salad",
        "description": "Sliced grilled chicken breast over mixed greens, cucumber, and light lemon herb vinaigrette.",
        "meal_type": ["lunch"],
        "ingredients": ["chicken", "mixed greens", "cucumber", "olive oil", "lemon", "herbs"],
        "dietary": ["gluten-free", "low-carb", "dairy-free"],
        "prep_time_minutes": 15,
        "difficulty": "Easy",
        "instructions": [
            "Grill or pan-sear chicken breast until 165°F (74°C); let rest and slice.",
            "Toss mixed baby greens and cucumber slices in a bowl.",
            "Top with warm chicken slices and dress with lemon herb vinaigrette."
        ],
        "nutrition_per_serving": {
            "calories": 330,
            "protein_g": 38,
            "carbs_g": 6,
            "fat_g": 15
        }
    },
    {
        "name": "Classic Chicken Fried Rice",
        "description": "Savory wok-fried jasmine rice with seasoned chicken bits, scrambled egg, and scallions.",
        "meal_type": ["lunch", "dinner"],
        "ingredients": ["chicken", "rice", "eggs", "soy sauce", "garlic", "green onions"],
        "dietary": ["dairy-free"],
        "prep_time_minutes": 20,
        "difficulty": "Easy",
        "instructions": [
            "Cook diced chicken in a hot wok until cooked through; push to the side.",
            "Pour beaten eggs into the empty side of the pan and scramble quickly.",
            "Add chilled day-old rice, breaking up any clumps.",
            "Drizzle soy sauce, add garlic and green onions, and toss over high heat for 3-4 minutes."
        ],
        "nutrition_per_serving": {
            "calories": 420,
            "protein_g": 28,
            "carbs_g": 48,
            "fat_g": 12
        }
    },
    {
        "name": "Lentil & Spinach Soup with Warm Pita",
        "description": "Hearty French green lentils simmered with mirepoix vegetables and wilted baby spinach.",
        "meal_type": ["lunch"],
        "ingredients": ["lentils", "carrots", "celery", "onions", "spinach", "vegetable broth"],
        "dietary": ["vegan", "vegetarian", "dairy-free"],
        "prep_time_minutes": 30,
        "difficulty": "Easy",
        "instructions": [
            "Sauté diced carrots, celery, and onions in olive oil until soft.",
            "Add rinsed lentils and vegetable broth; simmer for 25 minutes until lentils are tender.",
            "Stir in fresh spinach until wilted, season with salt and pepper, and serve warm."
        ],
        "nutrition_per_serving": {
            "calories": 310,
            "protein_g": 17,
            "carbs_g": 50,
            "fat_g": 4
        }
    },
    {
        "name": "Caprese Pesto Pasta Salad",
        "description": "Al dente penne pasta tossed with basil pesto, cherry tomatoes, and mini mozzarella pearls.",
        "meal_type": ["lunch"],
        "ingredients": ["pasta", "pesto", "tomatoes", "mozzarella", "basil"],
        "dietary": ["vegetarian"],
        "prep_time_minutes": 15,
        "difficulty": "Easy",
        "instructions": [
            "Boil pasta until al dente; drain and rinse with cold water.",
            "Toss pasta with basil pesto in a large bowl.",
            "Fold in halved cherry tomatoes, fresh basil leaves, and mozzarella pearls."
        ],
        "nutrition_per_serving": {
            "calories": 390,
            "protein_g": 14,
            "carbs_g": 46,
            "fat_g": 18
        }
    },

    # Dinners
    {
        "name": "Garlic Herb Chicken & Tomatoes",
        "description": "Pan-seared chicken breasts simmered with fresh garlic, cherry tomatoes, and herbs.",
        "meal_type": ["dinner"],
        "ingredients": ["chicken", "garlic", "tomatoes", "olive oil", "herbs"],
        "dietary": ["gluten-free", "low-carb", "dairy-free"],
        "prep_time_minutes": 25,
        "difficulty": "Easy",
        "instructions": [
            "Season chicken breasts with salt and pepper.",
            "Heat olive oil in a skillet over medium-high heat and sear chicken for 6-8 minutes per side.",
            "Add minced garlic and halved cherry tomatoes; sauté for 3-4 minutes until tomatoes blister.",
            "Garnish with fresh herbs and serve hot."
        ],
        "nutrition_per_serving": {
            "calories": 340,
            "protein_g": 42,
            "carbs_g": 8,
            "fat_g": 14
        }
    },
    {
        "name": "Crispy Tofu & Vegetable Stir-Fry",
        "description": "Cubed crispy tofu with broccoli florets and bell peppers tossed in a savory soy-garlic glaze.",
        "meal_type": ["dinner"],
        "ingredients": ["tofu", "broccoli", "bell pepper", "soy sauce", "garlic", "sesame oil"],
        "dietary": ["vegan", "vegetarian", "dairy-free"],
        "prep_time_minutes": 20,
        "difficulty": "Medium",
        "instructions": [
            "Press tofu to remove excess moisture and cut into bite-sized cubes.",
            "Pan-fry tofu in oil until golden brown on all sides; remove and set aside.",
            "Sauté broccoli florets and sliced bell peppers with minced garlic until tender-crisp.",
            "Add tofu back into the skillet, pour in soy sauce and sesame oil, and toss to coat."
        ],
        "nutrition_per_serving": {
            "calories": 280,
            "protein_g": 18,
            "carbs_g": 16,
            "fat_g": 15
        }
    },
    {
        "name": "Sheet Pan Lemon Herb Salmon & Asparagus",
        "description": "Tender baked salmon fillet with fresh asparagus spears and lemon garlic butter.",
        "meal_type": ["dinner"],
        "ingredients": ["salmon", "asparagus", "olive oil", "lemon", "garlic", "dill"],
        "dietary": ["gluten-free", "low-carb", "dairy-free"],
        "prep_time_minutes": 20,
        "difficulty": "Easy",
        "instructions": [
            "Preheat oven to 400°F (200°C) and line a sheet pan with parchment.",
            "Arrange salmon fillets and trimmed asparagus spears on the pan.",
            "Drizzle with olive oil, minced garlic, lemon slices, and fresh dill.",
            "Bake for 12-15 minutes until salmon flakes easily with a fork."
        ],
        "nutrition_per_serving": {
            "calories": 390,
            "protein_g": 36,
            "carbs_g": 6,
            "fat_g": 24
        }
    },
    {
        "name": "Coconut Chickpea & Spinach Curry",
        "description": "Aromatic golden curry simmered with chickpeas, rich coconut milk, and tender baby spinach.",
        "meal_type": ["dinner"],
        "ingredients": ["chickpeas", "coconut milk", "spinach", "curry powder", "garlic", "ginger", "rice"],
        "dietary": ["vegan", "vegetarian", "gluten-free", "dairy-free"],
        "prep_time_minutes": 25,
        "difficulty": "Easy",
        "instructions": [
            "Sauté minced garlic and grated ginger in olive oil for 1 minute.",
            "Stir in curry powder and cumin until fragrant.",
            "Pour in coconut milk and rinsed chickpeas; simmer for 15 minutes.",
            "Fold in fresh baby spinach until wilted and serve over steamed jasmine rice."
        ],
        "nutrition_per_serving": {
            "calories": 410,
            "protein_g": 12,
            "carbs_g": 48,
            "fat_g": 21
        }
    },
    {
        "name": "Baked Zucchini Lasagna Boats",
        "description": "Hollowed roasted zucchini boats filled with marinara, ricotta, and melted mozzarella.",
        "meal_type": ["dinner"],
        "ingredients": ["zucchini", "marinara sauce", "ricotta", "mozzarella", "parmesan", "garlic"],
        "dietary": ["vegetarian", "gluten-free", "low-carb"],
        "prep_time_minutes": 30,
        "difficulty": "Medium",
        "instructions": [
            "Cut zucchini in half lengthwise and scoop out centers to make boats.",
            "Fill boats with seasoned ricotta, marinara sauce, and minced garlic.",
            "Top with shredded mozzarella and parmesan cheese.",
            "Bake at 375°F (190°C) for 22-25 minutes until cheese is bubbly and golden."
        ],
        "nutrition_per_serving": {
            "calories": 310,
            "protein_g": 20,
            "carbs_g": 14,
            "fat_g": 19
        }
    },
    {
        "name": "Beef & Broccoli Skillet Stir-Fry",
        "description": "Tender flank steak strips and broccoli florets tossed in a rich ginger-tamari reduction.",
        "meal_type": ["dinner"],
        "ingredients": ["beef", "broccoli", "soy sauce", "ginger", "garlic", "sesame oil"],
        "dietary": ["gluten-free", "dairy-free", "low-carb"],
        "prep_time_minutes": 20,
        "difficulty": "Easy",
        "instructions": [
            "Slice flank steak thinly across the grain.",
            "Sear beef in a very hot skillet for 2-3 minutes; transfer to a plate.",
            "Steam-fry broccoli with garlic and ginger until bright green.",
            "Return beef to skillet, add tamari and sesame oil, and toss for 1 minute."
        ],
        "nutrition_per_serving": {
            "calories": 360,
            "protein_g": 35,
            "carbs_g": 10,
            "fat_g": 18
        }
    },
    {
        "name": "Black Bean & Corn Stuffed Peppers",
        "description": "Sweet bell peppers stuffed with seasoned black beans, sweet corn, salsa, and melted cheddar.",
        "meal_type": ["dinner"],
        "ingredients": ["bell pepper", "black beans", "corn", "salsa", "cheddar cheese", "cumin"],
        "dietary": ["vegetarian", "gluten-free"],
        "prep_time_minutes": 35,
        "difficulty": "Easy",
        "instructions": [
            "Cut tops off bell peppers and remove seeds.",
            "Mix black beans, sweet corn, salsa, cumin, and half the cheese in a bowl.",
            "Stuff peppers firmly with mixture and place in a baking dish with a splash of water.",
            "Top with remaining cheese and bake at 375°F (190°C) for 30 minutes."
        ],
        "nutrition_per_serving": {
            "calories": 340,
            "protein_g": 16,
            "carbs_g": 48,
            "fat_g": 11
        }
    }
]


def find_recipes(ingredients: List[str], dietary_preference: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for recipe recommendations matching the user's available ingredients and dietary preferences.

    Args:
        ingredients: A list of ingredient names the user has on hand (e.g. ['chicken', 'garlic', 'tomatoes']).
        dietary_preference: Optional dietary filter (e.g. 'vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'low-carb').

    Returns:
        A list of matching recipe summaries including recipe name, matching ingredients, missing ingredients, prep time, and difficulty.
    """
    normalized_input = [ing.strip().lower() for ing in ingredients if ing.strip()]
    results = []

    for recipe in RECIPE_DATABASE:
        recipe_ings = [i.lower() for i in recipe["ingredients"]]
        dietary_tags = [d.lower() for d in recipe["dietary"]]

        if dietary_preference:
            norm_diet = dietary_preference.strip().lower()
            if norm_diet and norm_diet not in dietary_tags:
                continue

        matched = []
        for user_ing in normalized_input:
            for r_ing in recipe_ings:
                if user_ing in r_ing or r_ing in user_ing:
                    if r_ing not in matched:
                        matched.append(r_ing)

        missing = [i for i in recipe_ings if i not in matched]

        if matched:
            results.append({
                "recipe_name": recipe["name"],
                "description": recipe["description"],
                "matched_ingredients": matched,
                "missing_ingredients": missing,
                "prep_time_minutes": recipe["prep_time_minutes"],
                "difficulty": recipe["difficulty"],
                "instructions": recipe["instructions"]
            })

    results.sort(key=lambda r: len(r["matched_ingredients"]), reverse=True)
    return results


def calculate_nutrition_estimate(recipe_name: str, servings: int = 1) -> Dict[str, Any]:
    """Calculate the estimated nutritional breakdown for a given recipe scaled to a specific number of servings.

    Args:
        recipe_name: Name of the recipe to calculate nutrition for.
        servings: Number of servings (default is 1).

    Returns:
        A dictionary with calories, protein (g), carbohydrates (g), and fat (g) for the specified servings.
    """
    servings = max(1, servings)
    norm_name = recipe_name.strip().lower()

    for recipe in RECIPE_DATABASE:
        if norm_name in recipe["name"].lower() or recipe["name"].lower() in norm_name:
            base = recipe["nutrition_per_serving"]
            return {
                "recipe_name": recipe["name"],
                "servings": servings,
                "total_calories": base["calories"] * servings,
                "protein_g": base["protein_g"] * servings,
                "carbs_g": base["carbs_g"] * servings,
                "fat_g": base["fat_g"] * servings,
                "per_serving": base
            }

    default_base = {"calories": 350, "protein_g": 20, "carbs_g": 30, "fat_g": 12}
    return {
        "recipe_name": recipe_name,
        "servings": servings,
        "total_calories": default_base["calories"] * servings,
        "protein_g": default_base["protein_g"] * servings,
        "carbs_g": default_base["carbs_g"] * servings,
        "fat_g": default_base["fat_g"] * servings,
        "per_serving": default_base,
        "note": "Estimated based on average home-cooked meal profile."
    }


def generate_weekly_meal_plan(
    dietary_preference: Optional[str] = None,
    days_count: int = 7,
    servings: int = 2
) -> Dict[str, Any]:
    """Generate a structured, 7-day meal prep plan for every meal of the week (Breakfast, Lunch, Dinner).

    Args:
        dietary_preference: Optional dietary restriction (e.g. 'vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'low-carb').
        days_count: Number of days to plan (default 7 for Monday through Sunday).
        servings: Number of portions/people to prepare for (default 2).

    Returns:
        A complete weekly meal plan including day-by-day recipes for breakfast, lunch, and dinner,
        estimated daily nutrition totals, a Sunday batch prep strategy, and a consolidated grocery checklist.
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_to_plan = min(len(day_names), max(1, days_count))

    def matches_diet(recipe: Dict[str, Any]) -> bool:
        if not dietary_preference:
            return True
        norm = dietary_preference.strip().lower()
        return norm in [d.lower() for d in recipe.get("dietary", [])]

    eligible_recipes = [r for r in RECIPE_DATABASE if matches_diet(r)]
    if len(eligible_recipes) < 3:
        eligible_recipes = RECIPE_DATABASE

    breakfasts = [r for r in eligible_recipes if "breakfast" in r.get("meal_type", [])] or eligible_recipes
    lunches = [r for r in eligible_recipes if "lunch" in r.get("meal_type", [])] or eligible_recipes
    dinners = [r for r in eligible_recipes if "dinner" in r.get("meal_type", [])] or eligible_recipes

    schedule = []
    all_ingredients = set()

    for idx in range(days_to_plan):
        day_name = day_names[idx]
        b_recipe = breakfasts[idx % len(breakfasts)]
        l_recipe = lunches[idx % len(lunches)]
        d_recipe = dinners[idx % len(dinners)]

        for r in (b_recipe, l_recipe, d_recipe):
            for ing in r["ingredients"]:
                all_ingredients.add(ing)

        day_calories = (
            b_recipe["nutrition_per_serving"]["calories"] +
            l_recipe["nutrition_per_serving"]["calories"] +
            d_recipe["nutrition_per_serving"]["calories"]
        )

        schedule.append({
            "day": day_name,
            "meals": {
                "breakfast": {
                    "name": b_recipe["name"],
                    "description": b_recipe["description"],
                    "prep_time_minutes": b_recipe["prep_time_minutes"],
                    "calories_per_serving": b_recipe["nutrition_per_serving"]["calories"],
                    "ingredients": b_recipe["ingredients"],
                    "instructions": b_recipe["instructions"]
                },
                "lunch": {
                    "name": l_recipe["name"],
                    "description": l_recipe["description"],
                    "prep_time_minutes": l_recipe["prep_time_minutes"],
                    "calories_per_serving": l_recipe["nutrition_per_serving"]["calories"],
                    "ingredients": l_recipe["ingredients"],
                    "instructions": l_recipe["instructions"]
                },
                "dinner": {
                    "name": d_recipe["name"],
                    "description": d_recipe["description"],
                    "prep_time_minutes": d_recipe["prep_time_minutes"],
                    "calories_per_serving": d_recipe["nutrition_per_serving"]["calories"],
                    "ingredients": d_recipe["ingredients"],
                    "instructions": d_recipe["instructions"]
                }
            },
            "daily_calories_per_person": day_calories,
            "servings": servings
        })

    grocery_departments = {
        "Produce": [],
        "Proteins & Dairy": [],
        "Grains & Pantry Staples": []
    }

    produce_keywords = {"spinach", "berries", "avocado", "lemon", "sweet potatoes", "bell pepper", "banana", "cucumber", "tomatoes", "kale", "romaine lettuce", "mixed greens", "green onions", "carrots", "celery", "onions", "garlic", "broccoli", "asparagus", "zucchini", "dill", "chives", "cilantro", "herbs"}
    protein_dairy_keywords = {"eggs", "cheddar cheese", "butter", "greek yogurt", "smoked salmon", "chicken", "tofu", "turkey breast", "mozzarella", "ricotta", "parmesan", "beef", "salmon"}

    for item in sorted(all_ingredients):
        if any(kw in item for kw in produce_keywords):
            grocery_departments["Produce"].append(item)
        elif any(kw in item for kw in protein_dairy_keywords):
            grocery_departments["Proteins & Dairy"].append(item)
        else:
            grocery_departments["Grains & Pantry Staples"].append(item)

    meal_prep_strategy = [
        "1. Prep Grains & Legumes (Sunday): Batch-cook jasmine rice and quinoa. Cool completely and portion into airtight glass containers for quick lunches.",
        "2. Chop Produce in Advance: Wash and slice cucumbers, bell peppers, carrots, and sweet potato cubes so weeknight cooking takes under 15 minutes.",
        "3. Mason Jar Pre-Packing: Pre-assemble overnight chia oats or lunch salads (dressing on the bottom) for grab-and-go mornings.",
        "4. Protein Seasoning: Pre-portion chicken/salmon fillets and marinate with olive oil, garlic, and herbs before freezing or chilling."
    ]

    return {
        "plan_title": f"{dietary_preference.capitalize() if dietary_preference else 'Balanced'} 7-Day Meal Prep Schedule",
        "dietary_preference": dietary_preference or "none",
        "days_planned": days_to_plan,
        "servings": servings,
        "schedule": schedule,
        "batch_prep_strategy": meal_prep_strategy,
        "grocery_list": grocery_departments
    }


def get_pantry_inventory() -> List[Dict[str, Any]]:
    """Retrieve all food items currently in the user's pantry and refrigerator from the Firestore database.

    Returns:
        A list of pantry items with their name, category, quantity, unit, and shelf life days.
    """
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        docs = db.collection("pantry_inventory").stream()
        items = [doc.to_dict() for doc in docs]
        return items if items else [{"note": "Pantry inventory is currently empty."}]
    except Exception as e:
        return [{"error": f"Failed to retrieve pantry inventory: {e}"}]


def add_or_update_pantry_item(
    item_name: str,
    quantity: float,
    unit: str,
    category: str = "pantry",
    expiry_days: int = 7
) -> Dict[str, Any]:
    """Add a new item or update quantity of an existing item in the user's Firestore pantry database.

    Args:
        item_name: Name of the food item (e.g. 'eggs', 'spinach', 'almond milk').
        quantity: Numerical quantity (e.g. 2, 0.5, 12).
        unit: Unit of measure (e.g. 'lbs', 'count', 'oz', 'carton', 'bag').
        category: Storage category ('produce', 'dairy', 'protein', 'pantry').
        expiry_days: Estimated days before expiration.

    Returns:
        Confirmation status of the added or updated item.
    """
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc_id = item_name.strip().lower().replace(" ", "_")
        data = {
            "item_name": item_name.strip().lower(),
            "quantity": quantity,
            "unit": unit.strip().lower(),
            "category": category.strip().lower(),
            "expiry_days": expiry_days
        }
        db.collection("pantry_inventory").document(doc_id).set(data)
        return {"status": "success", "message": f"Updated pantry with {quantity} {unit} of {item_name}.", "item": data}
    except Exception as e:
        return {"status": "error", "message": f"Failed to update pantry: {e}"}


def find_ingredient_substitute(ingredient_name: str) -> Dict[str, Any]:
    """Find reliable, culinary-tested ingredient substitutes with exact substitution ratios when an item is missing or restricted.

    Args:
        ingredient_name: The ingredient you need a substitute for (e.g. 'sour cream', 'buttermilk', 'eggs', 'butter', 'soy sauce').

    Returns:
        Best substitute option, ratio, and chef's tips.
    """
    COMMON_SUBSTITUTES = {
        "buttermilk": {"substitute": "1 cup milk + 1 tbsp lemon juice or white vinegar", "ratio": "1:1", "notes": "Let sit 5 minutes to curdle before using."},
        "sour cream": {"substitute": "Plain whole-milk Greek yogurt", "ratio": "1:1", "notes": "Identical tang and moisture profile with extra protein."},
        "heavy cream": {"substitute": "3/4 cup milk + 1/4 cup melted butter, or canned coconut cream", "ratio": "1:1", "notes": "Full-fat coconut cream works wonders for dairy-free."},
        "butter": {"substitute": "Extra virgin olive oil (sautéing) or applesauce/coconut oil (baking)", "ratio": "3/4 cup oil per 1 cup butter", "notes": "Excellent heart-healthy or dairy-free alternative."},
        "eggs": {"substitute": "1 tbsp ground flaxseeds or chia seeds + 3 tbsp water (per egg)", "ratio": "1 egg = 1 flax egg", "notes": "Let rest 5 mins until gelled; great for pancakes and muffins."},
        "cornstarch": {"substitute": "All-purpose flour or arrowroot starch", "ratio": "2 tbsp flour per 1 tbsp cornstarch", "notes": "Simmer 2 mins longer to cook out raw flour taste."},
        "garlic": {"substitute": "Garlic powder or minced shallots", "ratio": "1/8 tsp garlic powder per fresh clove", "notes": "Shallots give a milder, sweeter aroma."},
        "soy sauce": {"substitute": "Tamari (gluten-free) or coconut aminos (soy-free)", "ratio": "1:1", "notes": "Coconut aminos is naturally sweeter and lower in sodium."},
        "lemon juice": {"substitute": "Apple cider vinegar or white wine vinegar", "ratio": "1/2 tbsp vinegar per 1 tbsp lemon juice", "notes": "Provides identical acid lift in savory dressings."},
        "breadcrumbs": {"substitute": "Crushed rolled oats, almond flour, or panko", "ratio": "1:1", "notes": "Almond flour adds pleasant nuttiness for low-carb/keto dishes."}
    }

    norm = ingredient_name.strip().lower()
    if norm in COMMON_SUBSTITUTES:
        info = COMMON_SUBSTITUTES[norm]
        return {
            "searched_ingredient": ingredient_name,
            "recommended_substitute": info["substitute"],
            "ratio": info["ratio"],
            "chef_tip": info["notes"]
        }

    for key, info in COMMON_SUBSTITUTES.items():
        if key in norm or norm in key:
            return {
                "searched_ingredient": ingredient_name,
                "recommended_substitute": info["substitute"],
                "ratio": info["ratio"],
                "chef_tip": info["notes"]
            }

    return {
        "searched_ingredient": ingredient_name,
        "recommended_substitute": f"Look for a complementary flavor in the same culinary category (e.g. similar acid, fat, or grain profile).",
        "ratio": "Adjust to taste (1:1 standard)",
        "chef_tip": "When substituting unfamiliar spices or aromatics, start with half the amount and taste test."
    }


def search_herbal_culinary_lore(query: str) -> str:
    """Search Culpeper's Complete Herbal and historical culinary lore for herbal remedies, flavor pairings, and plant properties.

    Args:
        query: What herb, plant, ailment, or culinary flavoring to look up (e.g. 'thyme', 'mint', 'sage', 'indigestion').

    Returns:
        The matched excerpts and culinary knowledge from the corpus.
    """
    from vertexai.preview import rag
    import vertexai

    vertexai.init(project=FIRESTORE_PROJECT_ID, location="us-central1")
    try:
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        return "\n\n---\n\n".join(passages) or "No relevant passage found in herbal corpus."
    except Exception as e:
        return f"Herbal retrieval note: {e}"


def generate_dish_image(dish_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate an appetizing presentation photo of a dish using gemini-3.1-flash-lite-image in the global region.
    Saves the image bytes as a session artifact and uploads to the public Cloud Storage bucket for web display.

    Args:
        dish_name: Name and styling description of the culinary dish (e.g. 'Golden Spinach and Cheddar Omelet with Herbs').

    Returns:
        A dictionary with the public Cloud Storage image URL, filename, and presentation status.
    """
    from google import genai
    import uuid

    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = (
        f"Professional culinary food photography of {dish_name}, "
        "expertly plated on a warm ceramic dish, natural studio lighting, mouthwatering presentation, 8k resolution, photorealistic."
    )

    try:
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        for part in res.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            return {"status": "error", "message": "No image data returned from image generation model."}

        # 1. Save artifact to ToolContext for the Playground's Artifacts panel (if available)
        safe_name = "".join(c if c.isalnum() else "_" for c in dish_name.lower())[:30].strip("_")
        artifact_filename = f"{safe_name}_{uuid.uuid4().hex[:6]}.jpg"

        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    custom_metadata={"dish_name": dish_name, "type": "dish_presentation_photo"}
                )
            except Exception as se:
                print(f"Artifact save skipped: {se}")

        # 2. Upload same bytes to public Cloud Storage bucket
        public_url = ""
        try:
            storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
            bucket = storage_client.bucket(IMAGE_BUCKET_NAME)
            blob_path = f"dishes/{artifact_filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_string(image_bytes, content_type="image/jpeg")
            public_url = f"https://storage.googleapis.com/{IMAGE_BUCKET_NAME}/{blob_path}"
        except Exception as upload_err:
            print(f"Bucket upload optional step skipped or failed: {upload_err}")

        return {
            "status": "success",
            "dish_name": dish_name,
            "artifact_filename": artifact_filename,
            "public_image_url": public_url,
            "message": f"Successfully generated and published photo for {dish_name}!"
        }
    except Exception as e:
        return {"status": "error", "message": f"Image generation failed: {e}"}
