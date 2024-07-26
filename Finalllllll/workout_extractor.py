import google.generativeai as genai
from typing import List, Dict, Union
import re
import logging
import json

class WorkoutExtractor:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_workout_plan(self, ai_response: str) -> List[Dict[str, Union[str, List[Dict[str, Union[str, int, bool]]]]]]:
        prompt = f"""
        You are a precise workout plan formatter. Your task is to take the following 7-day workout plan and reformat it into a strictly structured JSON format. Follow these rules exactly:

        1. The output must be a valid JSON array containing exactly 7 objects, one for each day.
        2. Each day object must have a "day" key (e.g., "Day 1") and an "exercises" array.
        3. Each exercise in the "exercises" array must have these exact keys: "name", "sets", "reps", and "is_timed".
        4. For timed exercises, "reps" represents duration in seconds, and "is_timed" must be true.
        5. For non-timed exercises, "is_timed" must be false.
        6. All numerical values (sets, reps) must be integers, not strings.
        7. Do not include any explanations or additional text outside the JSON structure.

        Here's the workout plan to format:

        {ai_response}

        Expected output format:
        [
            {{
                "day": "Day 1",
                "exercises": [
                    {{"name": "Push-ups", "sets": 3, "reps": 10, "is_timed": false}},
                    {{"name": "Plank", "sets": 1, "reps": 60, "is_timed": true}},
                    {{"name": "Squats", "sets": 3, "reps": 15, "is_timed": false}}
                ]
            }},
            {{
                "day": "Day 2",
                "exercises": [
                    {{"name": "Jumping Jacks", "sets": 1, "reps": 30, "is_timed": true}},
                    {{"name": "Lunges", "sets": 3, "reps": 12, "is_timed": false}},
                    {{"name": "Mountain Climbers", "sets": 1, "reps": 45, "is_timed": true}}
                ]
            }},
            // ... (Days 3-6 would be listed here in the same format)
            {{
                "day": "Day 7",
                "exercises": [
                    {{"name": "Rest Day", "sets": 1, "reps": 1, "is_timed": false}}
                ]
            }}
        ]

        Ensure your output:
        1. Contains exactly 7 day objects.
        2. Uses the correct exercise format for each exercise type (timed vs. non-timed).
        3. Includes all exercises mentioned in the original plan.
        4. Does not add any exercises not mentioned in the original plan.
        5. Uses appropriate "sets" and "reps" values based on the original plan.

        Format the provided workout plan strictly according to these instructions and example.
        """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip('```json').strip('```').strip()
            
            logging.info(f"Raw AI response:\n{response_text}")

            try:
                workout_plan = json.loads(response_text)
                if isinstance(workout_plan, list):
                    return workout_plan
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON: {str(e)}")
                return self.clean_and_structure_response(response_text)

        except Exception as e:
            logging.error(f"Error in extract_workout_plan: {str(e)}")
            return self.clean_and_structure_response(ai_response)

    def clean_and_structure_response(self, response_text: str) -> List[Dict[str, Union[str, List[Dict[str, Union[str, int, bool]]]]]]:
        if not isinstance(response_text, str):
            logging.error(f"Invalid response_text type: {type(response_text)}")
            return self.generate_default_plan()

        workout_plan = []
        days = re.findall(r'Day \d+:(.*?)(?=Day \d+:|$)', response_text, re.DOTALL)

        if not days:
            logging.warning("No day patterns found in the response")
            return self.generate_default_plan()

        for i, day_content in enumerate(days, 1):
            exercises = []
            exercise_matches = re.findall(r'([\w\s]+):\s*(\d+(?:\s*x\s*\d+)?)\s*((?:reps|seconds))', day_content, re.IGNORECASE)
            
            for exercise_name, reps_or_duration, unit in exercise_matches:
                exercise = {
                    "name": exercise_name.strip(),
                    "is_timed": unit.lower() == "seconds"
                }
                
                if 'x' in reps_or_duration:
                    sets, reps = map(int, reps_or_duration.split('x'))
                    exercise["sets"] = sets
                    exercise["reps"] = reps
                else:
                    exercise["sets"] = 1
                    exercise["reps"] = int(reps_or_duration)

                exercises.append(exercise)

            workout_plan.append({
                "day": f"Day {i}",
                "exercises": exercises
            })

        if not workout_plan:
            logging.warning("Failed to extract exercises from the response")
            return self.generate_default_plan()

        return workout_plan

    def generate_default_plan(self) -> List[Dict[str, Union[str, List[Dict[str, Union[str, int, bool]]]]]]:
        logging.warning("Generating default workout plan")
        default_plan = []
        for i in range(1, 8):
            default_plan.append({
                "day": f"Day {i}",
                "exercises": [
                    {"name": "Push-ups", "sets": 3, "reps": 10, "is_timed": False},
                    {"name": "Squats", "sets": 3, "reps": 15, "is_timed": False},
                    {"name": "Plank", "sets": 1, "reps": 30, "is_timed": True}
                ]
            })
        return default_plan