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
        As an AI Fitness Assistant, your task is to interpret the user's request to adjust an exercise form threshold. The user is providing sufficient information, so you must make a determination based on the given input.

        Current thresholds:
        {json.dumps(current_thresholds, indent=2)}

        User's adjustment request: "{user_input}"

        Guidelines:
        1. You MUST identify the exercise (squat or bicep_curl), the feedback condition, and the adjustment direction (increase or decrease).
        2. If the exercise is not explicitly mentioned, infer it from context. Default to 'squat' if truly ambiguous.
        3. Match the feedback condition to the closest predefined condition, even if it's not an exact match.
        4. If the adjustment direction is not clear, make a reasonable inference based on the context.
        5. Always suggest a new threshold value that makes sense for the exercise and condition.

        Possible feedback conditions:
        Squat: squat_too_deep, squat_not_deep_enough, squat_forward_bend_too_little, squat_forward_bend_too_much
        Bicep Curl: bicep_curl_not_low_enough, bicep_curl_not_high_enough, bicep_curl_elbow_movement, bicep_curl_body_swing

        You MUST respond with a JSON object containing:
        {{
          "exercise": "squat" or "bicep_curl",
          "feedback_condition": <matched_condition>,
          "adjustment": "increase" or "decrease",
          "new_threshold": <suggested_new_value>,
          "confidence": <value_between_0_and_1>
        }}

        Analyze the user's input carefully and provide your best interpretation, even if you're not 100% certain. Use the confidence field to indicate your level of certainty in your interpretation.
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

                confidence = result.get("confidence", 0.5)  # Default to 0.5 if not provided

                # Log any mismatches for debugging, but proceed with the AI's interpretation
                if parsed_exercise and result.get("exercise") != parsed_exercise:
                    self.logger.info(f"Exercise interpretation: parsed {parsed_exercise}, AI suggested {result.get('exercise')}")
                if parsed_feedback and result.get("feedback_condition") != parsed_feedback:
                    self.logger.info(f"Feedback condition interpretation: parsed {parsed_feedback}, AI suggested {result.get('feedback_condition')}")
                if parsed_adjustment and result.get("adjustment") != parsed_adjustment:
                    self.logger.info(f"Adjustment interpretation: parsed {parsed_adjustment}, AI suggested {result.get('adjustment')}")

                explanation = f"Adjusted threshold for {result.get('exercise')} {result.get('feedback_condition')} to {new_threshold}"
                return new_threshold, explanation, confidence

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
                    explanation = f"Best guess: Adjusted threshold for {exercise} {feedback_condition} to {new_threshold}"
                    return new_threshold, explanation, 0.5  # Low confidence for best guess

        return None, "Failed to process the request. Please try again with different wording.", 0