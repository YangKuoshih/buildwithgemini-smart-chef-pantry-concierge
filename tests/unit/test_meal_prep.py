"""Unit tests for the Weekly Meal Prep Planner tool."""

import pytest
from app.tools import generate_weekly_meal_plan, find_recipes, calculate_nutrition_estimate


def test_generate_weekly_meal_plan_default():
    """Verify that default generation produces a 7-day schedule with 3 meals per day."""
    plan = generate_weekly_meal_plan()
    assert plan["days_planned"] == 7
    assert len(plan["schedule"]) == 7
    assert "batch_prep_strategy" in plan
    assert len(plan["batch_prep_strategy"]) > 0
    assert "grocery_list" in plan
    assert "Produce" in plan["grocery_list"]

    # Check each day has breakfast, lunch, and dinner
    for day in plan["schedule"]:
        assert "day" in day
        assert "breakfast" in day["meals"]
        assert "lunch" in day["meals"]
        assert "dinner" in day["meals"]
        assert day["daily_calories_per_person"] > 0
        assert len(day["meals"]["breakfast"]["instructions"]) > 0


def test_generate_weekly_meal_plan_vegetarian():
    """Verify that dietary preference filtering is respected."""
    plan = generate_weekly_meal_plan(dietary_preference="vegetarian", days_count=5, servings=3)
    assert plan["days_planned"] == 5
    assert len(plan["schedule"]) == 5
    assert plan["servings"] == 3
    assert "Vegetarian" in plan["plan_title"]

    # Verify no meat dishes slipped into a vegetarian plan
    meat_keywords = ["chicken", "beef", "turkey", "salmon"]
    for day in plan["schedule"]:
        for meal_type in ["breakfast", "lunch", "dinner"]:
            meal = day["meals"][meal_type]
            for kw in meat_keywords:
                assert kw not in meal["name"].lower(), f"Found {kw} in vegetarian meal: {meal['name']}"


def test_grocery_list_and_batch_strategy():
    """Verify grocery list items and batch prep recommendations."""
    plan = generate_weekly_meal_plan(days_count=7)
    groceries = plan["grocery_list"]
    assert len(groceries["Produce"]) > 0
    assert len(groceries["Proteins & Dairy"]) > 0
    assert len(groceries["Grains & Pantry Staples"]) > 0

    # Batch prep strategy should contain prep instructions
    assert any("prep" in tip.lower() or "batch" in tip.lower() for tip in plan["batch_prep_strategy"])


def test_find_recipes_with_expanded_database():
    """Verify recipe search functions with the expanded database."""
    results = find_recipes(ingredients=["spinach", "eggs"])
    assert len(results) >= 1
    assert any("omelet" in r["recipe_name"].lower() for r in results)


def test_nutrition_calculation():
    """Verify nutritional estimates for recipes in the catalog."""
    nutr = calculate_nutrition_estimate("Spinach & Cheddar Omelet", servings=2)
    assert nutr["servings"] == 2
    assert nutr["total_calories"] == 580
    assert nutr["protein_g"] == 42
