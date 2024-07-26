import google.generativeai as genai
import json
from fuzzywuzzy import fuzz, process
import re
import logging
import time

class ThresholdAdjuster:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.exercise_mapping = {
            'squat': ['squat', 'squats', 'squatting'],
            'bicep_curl': ['bicep curl', 'bicep curls', 'curl', 'curls', 'bicep', 'biceps']
        }
        
        self.feedback_mapping = {
            'squat_too_deep': ['too deep', 'squat too deep', 'going too low', 'low'],
            'squat_not_deep_enough': ['not deep enough', 'not low enough', 'too high', 'shallow'],
            'squat_forward_bend_too_little': ['not leaning forward enough', 'too upright', 'straight'],
            'squat_forward_bend_too_much': ['leaning too far forward', 'bending too much', 'leaning'],
            'bicep_curl_not_low_enough': ['not extending fully', 'not going low enough', 'high', 'not low'],
            'bicep_curl_not_high_enough': ['not curling high enough', 'not bringing weight up enough', 'low'],
            'bicep_curl_elbow_movement': ['elbow moving too much', 'unstable elbow', 'elbow'],
            'bicep_curl_body_swing': ['swinging body', 'using momentum', 'not stable', 'swing']
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def preprocess_input(self, user_input):
        return ' '.join(user_input.lower().split())

    def fuzzy_match(self, input_string, options, threshold=70):
        best_match, score = process.extractOne(input_string, options)
        return best_match if score >= threshold else None

    def parse_user_input(self, user_input):
        words = user_input.split()
        exercise = None
        feedback_condition = None
        adjustment = None

        # Fuzzy match exercise
        for word in words:
            for ex, synonyms in self.exercise_mapping.items():
                if self.fuzzy_match(word, synonyms):
                    exercise = ex
                    break
            if exercise:
                break

        # Fuzzy match feedback condition
        remaining_input = ' '.join(words)
        best_match = None
        best_score = 0
        for condition, phrases in self.feedback_mapping.items():
            for phrase in phrases:
                score = fuzz.partial_ratio(remaining_input, phrase)
                if score > best_score:
                    best_score = score
                    best_match = condition
        
        if best_score > 70:  # Adjust this threshold as needed
            feedback_condition = best_match

        # Determine adjustment direction
        if any(word in user_input for word in ['increase', 'more', 'higher', 'up']):
            adjustment = 'increase'
        elif any(word in user_input for word in ['decrease', 'less', 'lower', 'down']):
            adjustment = 'decrease'

        return exercise, feedback_condition, adjustment

    def generate_prompt(self, user_input, current_thresholds):
        prompt = f"""
        As an precise AI Fitness Assistant, your task is to accurately interpret the user's request to adjust an exercise form threshold to fit with the user's unique anatomy to help them have a better workout feedback. The user has provided sufficient information, so you must generate with an accurate response based on the user's request as well as the format requirement. 

        Current thresholds:
        {json.dumps(current_thresholds, indent=2)}

        Here's the User's adjustment request to format:  "{user_input}"

        Follow these guidelines exactly:
        1. You MUST identify the exercise (squat or bicep_curl), the feedback condition, and the adjustment direction (increase or decrease). 
        2. If the exercise is not explicitly mentioned, infer it from context. But the user will most likely include the name of the workout either "curl" (or "bicep curl") or "squat".
        3. Match the feedback condition to the closest predefined condition, even if it's not an exact match.
        4. The user's request will be guaranteed to contain sufficient information so try your best to give the user the best and most accurate response.
        5. Always suggest a new threshold value that makes sense for the exercise and the user's condition.
        6. Do not deviate from the guidelines or the formating requirement.

        Possible feedback conditions (the user prompt might not be exactly the same as these following but you have to keep the feedback condition format exactly like the following ):
        Squat: squat_too_deep, squat_not_deep_enough, squat_forward_bend_too_little, squat_forward_bend_too_much
        Bicep Curl: bicep_curl_not_low_enough, bicep_curl_not_high_enough, bicep_curl_elbow_movement, bicep_curl_body_swing

        You MUST respond with a valid JSON object containing exacty and strictly 4 objects. 
        Expected output format:
        {{
          "exercise": "squat" or "bicep_curl",
          "feedback_condition": <matched_condition>,
          "adjustment": "increase" or "decrease",
          "new_threshold": <suggested_new_value>
        }}
        DO not include any excessive or any other explaination. Only include the main content of the JSON object. 
        Format the provided user request strictly according to these instructions and example.
        Analyze the user's input carefully and provide your best interpretation, even if you're not 100% certain. 
        """
        return prompt

    def extract_json_from_response(self, response_text):
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            return None

    def adjust_threshold(self, user_input, current_thresholds, max_retries=3):
        cleaned_input = self.preprocess_input(user_input)
        parsed_exercise, parsed_feedback, parsed_adjustment = self.parse_user_input(cleaned_input)

        prompt = self.generate_prompt(cleaned_input, current_thresholds)

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                self.logger.info(f"API Response: {response.text}")

                result = self.extract_json_from_response(response.text)
                
                if result is None:
                    raise ValueError("Failed to extract JSON from the response")

                new_threshold = result.get("new_threshold")
                if new_threshold is None:
                    raise ValueError("No new threshold provided in the response")

                return new_threshold, "", 1  # Returning empty string for explanation and 1 for confidence

            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    # On final attempt, make a best guess based on parsed input
                    self.logger.warning("Making best guess based on parsed input")
                    exercise = parsed_exercise or "squat"  # Default to squat if not parsed
                    feedback_condition = parsed_feedback or next(iter(self.feedback_mapping))  # Use first feedback condition if not parsed
                    adjustment = parsed_adjustment or "increase"  # Default to increase if not parsed
                    current_value = current_thresholds.get(f"{exercise}_{feedback_condition}", 90)  # Default to 90 if not found
                    new_threshold = current_value + 5 if adjustment == "increase" else current_value - 5
                    return new_threshold, "", 1  # Returning empty string for explanation and 1 for confidence

        return None, "Failed to process the request. Please try again with different wording.", 1  # Returning 1 for confidence