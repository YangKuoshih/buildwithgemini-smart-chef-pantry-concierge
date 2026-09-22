import pytest
from app.tools import (
    find_ingredient_substitute,
    get_pantry_inventory,
    add_or_update_pantry_item,
    search_herbal_culinary_lore,
)

def test_find_ingredient_substitute():
    res = find_ingredient_substitute("sour cream")
    assert "Greek yogurt" in res["recommended_substitute"]
    assert res["ratio"] == "1:1"

    res_butter = find_ingredient_substitute("butter")
    assert "oil" in res_butter["recommended_substitute"].lower()

def test_pantry_inventory_read_write():
    # Test adding an item and reading it back
    update_res = add_or_update_pantry_item("test_apples", 5, "count", "produce", 10)
    assert update_res["status"] == "success"

    inventory = get_pantry_inventory()
    assert isinstance(inventory, list)
    assert any(item.get("item_name") == "test_apples" for item in inventory)

def test_search_herbal_culinary_lore():
    res = search_herbal_culinary_lore("rosemary")
    assert isinstance(res, str)
    assert len(res) > 0
