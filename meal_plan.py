import google.generativeai as genai
import json
import logging

class MealPlanExtractor:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_meal_plan(self, survey_data):
        prompt = f"""
        Create a 7-day meal plan based on the following information:
        - Weight: {survey_data['weight']} kg
        - Height: {survey_data['height']} cm
        - Gender: {survey_data['gender']}
        - Activity level: {survey_data['activity']}
        - Fitness goal: {survey_data['goal']}
        
        Format the meal plan as a JSON array with 7 objects, one for each day.
        Each day should have breakfast, lunch, dinner, and two snacks.
        
        Example format:
        [
            {{
                "day": "Day 1",
                "meals": {{
                    "breakfast": "Oatmeal with berries and nuts",
                    "morning_snack": "Apple with almond butter",
                    "lunch": "Grilled chicken salad with mixed greens",
                    "afternoon_snack": "Greek yogurt with honey",
                    "dinner": "Baked salmon with roasted vegetables"
                }}
            }},
            // ... (Days 2-7)
        ]
        """

        try:
            response = self.model.generate_content(prompt)
            meal_plan = json.loads(response.text)
            return meal_plan
        except Exception as e:
            logging.error(f"Error in extract_meal_plan: {str(e)}")
            return self.generate_default_meal_plan()

    def generate_default_meal_plan(self):
        # Create a simple default meal plan if extraction fails
        default_plan = []
        for i in range(1, 8):
            default_plan.append({
                "day": f"Day {i}",
                "meals": {
                    "breakfast": "Oatmeal with fruit",
                    "morning_snack": "Apple",
                    "lunch": "Chicken salad",
                    "afternoon_snack": "Yogurt",
                    "dinner": "Grilled fish with vegetables"
                }
            })
        return default_plan