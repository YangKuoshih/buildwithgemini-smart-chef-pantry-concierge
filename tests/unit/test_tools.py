import pytest
from app.tools import find_recipes, calculate_nutrition_estimate

def test_find_recipes_matching():
    results = find_recipes(ingredients=["chicken", "garlic", "tomatoes"])
    assert len(results) > 0
    top_recipe = results[0]
    assert top_recipe["recipe_name"] == "Garlic Herb Chicken & Tomatoes"
    assert "chicken" in top_recipe["matched_ingredients"]

def test_find_recipes_dietary_filter():
    results = find_recipes(ingredients=["eggs", "cheddar cheese"], dietary_preference="vegetarian")
    assert len(results) > 0
    assert any(r["recipe_name"] == "Spinach & Cheddar Omelet" for r in results)

def test_calculate_nutrition_estimate():
    nutrition = calculate_nutrition_estimate("Spinach & Cheddar Omelet", servings=2)
    assert nutrition["servings"] == 2
    assert nutrition["total_calories"] == 290 * 2
    assert nutrition["protein_g"] == 21 * 2
