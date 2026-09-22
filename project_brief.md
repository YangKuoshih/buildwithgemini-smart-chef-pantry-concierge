# My agent: Smart Chef & Pantry Concierge
One-liner: A conversational culinary agent that helps home cooks create delicious meals with ingredients they already own, tailored to their dietary needs and household size, presented through glanceable recipe cards and plating visuals.

Tool coverage:
- Memory: Remembers available pantry/fridge ingredients, household size, allergens, and dietary preferences across sessions
- Tools: Search recipe catalog by ingredients & dietary filters, calculate scaled nutrition/portion macros, and generate missing-item shopping lists
- Catalog/UI: Recipe collection rendered as A2UI cards with prep times, badges, ingredient checklists, and clear step-by-step instructions
- Image gen: Photorealistic plating and finished dish previews generated with Imagen
- Sandbox: Portion scaling math, metric-to-imperial unit conversions, and macronutrient calculations

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): A2UI recipe cards, Imagen dish visualization, custom-styled culinary chat UI
First eval question: Given a user who is vegetarian with a pantry containing eggs, spinach, and cheddar cheese, does the agent recommend a valid vegetarian dish, accurately identify the ingredients the user already has, and calculate realistic single-serving nutrition macros?
