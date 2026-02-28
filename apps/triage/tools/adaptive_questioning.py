"""
Tool: Adaptive Questioning Tool - NEW
Generates age-appropriate, complaint-specific follow-up questions
Implements WHO/ICRC triage principles for adaptive questioning
"""

from typing import Dict, Any, List, Optional, Tuple
import random


class AdaptiveQuestioningTool:
    """
    Generates adaptive follow-up questions based on:
    - Complaint group
    - Age group
    - Previously collected symptom indicators
    - WHO/ICRC triage guidelines
    """

    def __init__(self):
        # ====================================================================
        # Question trees by complaint group and age
        # ====================================================================
        
        self.QUESTION_TREES = {
            # ================================================================
            # FEVER / FEELING HOT
            # ================================================================
            'fever': {
                'description': 'Questions for fever assessment',
                'initial_questions': [
                    "How high is the fever? Do you have a thermometer reading?",
                    "Did the fever start suddenly or gradually?",
                ],
                'age_specific': {
                    'newborn': [
                        "Is the baby less than 2 months old? (This is very important)",
                        "Is the baby feeding normally?",
                        "Has the baby had any convulsions or fits?",
                        "Is the baby unusually sleepy or difficult to wake?",
                        "Is the baby's body stiff or floppy?",
                        "Has the baby stopped feeding completely?"
                    ],
                    'infant': [
                        "Is the child feeding/breastfeeding normally?",
                        "Have you noticed any difficulty breathing?",
                        "Has the child had any convulsions?",
                        "Is the child unusually sleepy or irritable?",
                        "Has the child been vomiting everything?",
                        "Have you checked for a rash?"
                    ],
                    'child_1_5': [
                        "Is the child able to drink fluids normally?",
                        "Have you noticed any difficulty breathing?",
                        "Has the child had any convulsions?",
                        "Is the child unusually sleepy or difficult to wake?",
                        "Has the child been vomiting?",
                        "Have you checked for a rash on the body?"
                    ],
                    'child_6_12': [
                        "Is the child able to drink fluids normally?",
                        "Has the child been vomiting?",
                        "Has there been any confusion or disorientation?",
                        "Have you noticed any difficulty breathing?",
                        "Does the child have a headache or body pains?",
                        "Have you given any medication for the fever?"
                    ],
                    'teen': [
                        "Do you have any other symptoms like headache, body aches, or vomiting?",
                        "Have you taken any medication for the fever?",
                        "Has the fever been going up and down or staying constant?",
                        "Have you noticed any confusion or dizziness?",
                        "Have you traveled recently or been in contact with sick people?"
                    ],
                    'adult': [
                        "Do you have any other symptoms like headache, body aches, or vomiting?",
                        "Have you taken any medication for the fever?",
                        "Has the fever been going up and down or staying constant?",
                        "Have you noticed any confusion or dizziness?",
                        "Have you traveled recently or been in contact with sick people?"
                    ],
                    'elderly': [
                        "Have you noticed any confusion or changes in mental state?",
                        "Are you able to drink fluids normally?",
                        "Have you fallen recently?",
                        "Do you have any chronic conditions like diabetes or heart disease?",
                        "Have you taken any medication for the fever?"
                    ],
                },
                'indicator_mapping': {
                    'feeding_normal': 'can_drink',
                    'convulsions': 'convulsions',
                    'lethargic': 'lethargic',
                    'difficulty_breathing': 'breathing_difficulty',
                    'vomiting': 'vomiting',
                    'confusion': 'confusion',
                    'rash': 'rash_present',
                }
            },
            
            # ================================================================
            # BREATHING / COUGH PROBLEM
            # ================================================================
            'breathing': {
                'description': 'Questions for respiratory symptoms',
                'initial_questions': [
                    "Are you having difficulty breathing or is it just coughing?",
                    "How long have you had these breathing problems?",
                ],
                'age_specific': {
                    'newborn': [
                        "Is the baby breathing faster than normal?",
                        "Is the baby making grunting sounds when breathing?",
                        "Is the baby's chest pulling in when breathing?",
                        "Are the baby's lips or face turning blue?",
                        "Is the baby feeding normally?",
                        "Has the baby stopped breathing at any time?"
                    ],
                    'infant': [
                        "Is the child breathing faster than normal?",
                        "Can you see the chest pulling in when breathing?",
                        "Is the child making whistling sounds when breathing?",
                        "Are the child's lips or face turning blue?",
                        "Is the child able to drink/breastfeed?",
                        "Is the child unusually sleepy or irritable?"
                    ],
                    'child_1_5': [
                        "Is the child breathing faster than normal?",
                        "Can you see the chest pulling in when breathing?",
                        "Is the child making whistling sounds when breathing?",
                        "Are the child's lips or face turning blue?",
                        "Is the child able to drink fluids normally?",
                        "Is the child unusually sleepy or difficult to wake?"
                    ],
                    'child_6_12': [
                        "Do you feel like you can't get enough air?",
                        "Do you have chest pain when breathing?",
                        "Are you wheezing or making noise when breathing?",
                        "Do you have a cough? Is it dry or wet?",
                        "Are you coughing up anything? What color?",
                        "Do you have a fever with this?"
                    ],
                    'teen': [
                        "Do you feel like you can't get enough air?",
                        "Do you have chest pain or tightness?",
                        "Are you wheezing or making noise when breathing?",
                        "Do you have a cough? Is it dry or producing phlegm?",
                        "Do you have a history of asthma or allergies?",
                        "Have you used any inhalers or medications?"
                    ],
                    'adult': [
                        "Do you feel like you can't get enough air?",
                        "Do you have chest pain or tightness?",
                        "Are you wheezing or making noise when breathing?",
                        "Do you have a cough? Is it dry or producing phlegm?",
                        "Do you have a history of asthma, COPD, or other lung problems?",
                        "Have you used any inhalers or medications?"
                    ],
                    'elderly': [
                        "Do you feel like you can't get enough air, even at rest?",
                        "Do you have chest pain or tightness?",
                        "Have you felt confused or unusually tired?",
                        "Do you have a cough? Are you coughing up phlegm?",
                        "Do you have any chronic lung conditions?",
                        "Have you had pneumonia before or been vaccinated against it?"
                    ],
                },
                'indicator_mapping': {
                    'fast_breathing': 'fast_breathing',
                    'chest_indrawing': 'chest_indrawing',
                    'wheezing': 'wheezing',
                    'blue_lips': 'blue_lips',
                    'grunting': 'grunting',
                    'cough': 'cough',
                    'chest_pain': 'chest_pain',
                }
            },
            
            # ================================================================
            # CHEST PAIN
            # ================================================================
            'chest_pain': {
                'description': 'Questions for chest pain assessment',
                'initial_questions': [
                    "Can you describe the chest pain? Is it sharp, crushing, or burning?",
                    "Did the pain start suddenly or gradually?",
                ],
                'age_specific': {
                    'adult': [
                        "Is the pain crushing or squeezing?",
                        "Does the pain spread to your arm, jaw, or back?",
                        "Are you short of breath with the pain?",
                        "Are you sweating or feeling nauseous?",
                        "Have you taken any medication for the pain?",
                        "Do you have a history of heart problems or high blood pressure?"
                    ],
                    'elderly': [
                        "Is the pain crushing or squeezing?",
                        "Does the pain spread to your arm, jaw, or back?",
                        "Are you short of breath with the pain?",
                        "Do you feel dizzy or lightheaded?",
                        "Do you have a history of heart problems or high blood pressure?",
                        "Have you taken any medication for the pain?"
                    ],
                    'teen': [
                        "Does the pain get worse when you breathe deeply or cough?",
                        "Did the pain start after an injury?",
                        "Have you had any fever or cough with this?",
                        "Does it hurt when someone presses on your chest?",
                        "Have you been doing any strenuous exercise?"
                    ],
                },
                'indicator_mapping': {
                    'crushing_pain': 'crushing_chest_pain',
                    'radiating_pain': 'radiating_pain',
                    'shortness_of_breath': 'shortness_of_breath',
                    'sweating': 'sweating',
                    'nausea': 'nausea',
                }
            },
            
            # ================================================================
            # ABDOMINAL PAIN / VOMITING / DIARRHEA
            # ================================================================
            'abdominal': {
                'description': 'Questions for gastrointestinal symptoms',
                'initial_questions': [
                    "Where exactly is the pain? Upper, lower, or all over?",
                    "Have you been vomiting or had diarrhea?",
                ],
                'age_specific': {
                    'newborn': [
                        "Is the baby's abdomen swollen or hard?",
                        "Has the baby been vomiting? Green or yellow color?",
                        "Has the baby passed stool? When?",
                        "Is the baby feeding normally?",
                        "Is the baby crying excessively or inconsolably?",
                        "Has the baby had any fever?"
                    ],
                    'infant': [
                        "Is the child's abdomen swollen or hard?",
                        "Has the child been vomiting? What color?",
                        "Has the child had diarrhea? How many times?",
                        "Is the child able to keep fluids down?",
                        "Is the child passing urine normally?",
                        "Is the child unusually sleepy or irritable?"
                    ],
                    'child_1_5': [
                        "Has the child been vomiting? How many times?",
                        "Has the child had diarrhea? How many times?",
                        "Is the child able to keep fluids down?",
                        "Is the child passing urine normally?",
                        "Is the child in a lot of pain?",
                        "Does the child have a fever?"
                    ],
                    'adult': [
                        "Is the pain constant or does it come and go?",
                        "Have you been vomiting? How many times?",
                        "Have you had diarrhea? How many times?",
                        "Are you able to keep fluids down?",
                        "Have you noticed any blood in vomit or stool?",
                        "Do you have a fever with this?"
                    ],
                    'elderly': [
                        "Is the pain constant or does it come and go?",
                        "Have you been vomiting? How many times?",
                        "Have you had diarrhea? How many times?",
                        "Are you able to keep fluids down?",
                        "Have you noticed any blood in vomit or stool?",
                        "Have you felt dizzy or lightheaded?"
                    ],
                },
                'indicator_mapping': {
                    'vomiting': 'vomiting',
                    'vomiting_all': 'vomiting_all',
                    'diarrhea': 'diarrhea',
                    'blood_in_stool': 'blood_in_stool',
                    'blood_in_vomit': 'blood_in_vomit',
                    'severe_pain': 'severe_abdominal_pain',
                    'can_drink': 'can_drink',
                }
            },
            
            # ================================================================
            # HEADACHE / CONFUSION / WEAKNESS
            # ================================================================
            'headache': {
                'description': 'Questions for neurological symptoms',
                'initial_questions': [
                    "Can you describe the headache? Is it the worst of your life?",
                    "Did it start suddenly like a thunderclap?",
                ],
                'age_specific': {
                    'adult': [
                        "Is this the worst headache you've ever had?",
                        "Did it start suddenly?",
                        "Do you have any weakness on one side of your body?",
                        "Do you have difficulty speaking or understanding?",
                        "Do you have any vision changes?",
                        "Do you have a fever or stiff neck?"
                    ],
                    'elderly': [
                        "Is this the worst headache you've ever had?",
                        "Did it start suddenly?",
                        "Do you have any weakness on one side of your body?",
                        "Do you have difficulty speaking or understanding?",
                        "Have you had any falls or head injury?",
                        "Are you taking blood thinners?"
                    ],
                },
                'indicator_mapping': {
                    'worst_headache': 'worst_headache',
                    'sudden_onset': 'sudden_headache',
                    'weakness_one_side': 'weakness_one_side',
                    'slurred_speech': 'slurred_speech',
                    'vision_changes': 'vision_changes',
                    'stiff_neck': 'stiff_neck',
                }
            },
            
            # ================================================================
            # PREGNANCY CONCERN
            # ================================================================
            'pregnancy': {
                'description': 'Questions for pregnancy-related concerns',
                'initial_questions': [
                    "How many weeks pregnant are you?",
                    "What specific concern do you have?",
                ],
                'age_specific': {
                    'teen': [
                        "Do you have any vaginal bleeding?",
                        "Do you have severe abdominal pain?",
                        "Have you had any fluid leaking?",
                        "Have you noticed decreased fetal movement?",
                        "Do you have severe headache or vision changes?",
                        "Do you have swelling in your hands or face?"
                    ],
                    'adult': [
                        "Do you have any vaginal bleeding?",
                        "Do you have severe abdominal pain?",
                        "Have you had any fluid leaking?",
                        "Have you noticed decreased fetal movement?",
                        "Do you have severe headache or vision changes?",
                        "Do you have swelling in your hands or face?"
                    ],
                },
                'indicator_mapping': {
                    'vaginal_bleeding': 'vaginal_bleeding',
                    'severe_abdominal_pain': 'severe_abdominal_pain',
                    'fluid_leaking': 'fluid_leaking',
                    'decreased_movement': 'decreased_fetal_movement',
                    'severe_headache': 'severe_headache',
                    'vision_changes': 'vision_changes',
                }
            },
            
            # ================================================================
            # BLEEDING / BLOOD LOSS
            # ================================================================
            'bleeding': {
                'description': 'Questions for bleeding assessment',
                'initial_questions': [
                    "Where is the bleeding coming from?",
                    "How much bleeding? Are you soaking through pads/cloths?",
                ],
                'age_specific': {
                    'adult': [
                        "Can you control the bleeding with pressure?",
                        "Are you feeling dizzy or lightheaded?",
                        "Have you fainted or felt like fainting?",
                        "What caused the bleeding? Injury or spontaneous?",
                        "Are you taking any blood thinners?",
                        "Do you have any chronic conditions like hemophilia?"
                    ],
                },
                'indicator_mapping': {
                    'uncontrolled_bleeding': 'uncontrolled_bleeding',
                    'dizziness': 'dizziness',
                    'fainting': 'fainting',
                    'on_blood_thinners': 'on_blood_thinners',
                }
            },
            
            # ================================================================
            # DEFAULT / OTHER
            # ================================================================
            'other': {
                'description': 'General questions for unspecified complaints',
                'initial_questions': [
                    "Can you describe your symptoms in more detail?",
                    "How long have you had these symptoms?",
                ],
                'age_specific': {
                    'default': [
                        "How severe are your symptoms on a scale of 1-10?",
                        "Are your symptoms getting better, worse, or staying the same?",
                        "Do you have any other symptoms?",
                        "Have you seen a doctor about this before?",
                        "Are you taking any medication for this?"
                    ]
                }
            }
        }
        
        # ====================================================================
        # Red flag triggers that should end questioning immediately
        # ====================================================================
        self.RED_FLAG_TRIGGERS = {
            'breathing': [
                'severe_breathing_difficulty',
                'chest_indrawing',
                'blue_lips',
                'grunting',
                'stridor'
            ],
            'fever': [
                'convulsions',
                'lethargic',
                'stiff_neck',
                'unable_to_drink'
            ],
            'abdominal': [
                'severe_abdominal_pain',
                'blood_in_stool',
                'blood_in_vomit',
                'vomiting_all'
            ],
            'headache': [
                'worst_headache',
                'sudden_headache',
                'weakness_one_side',
                'slurred_speech'
            ],
            'chest_pain': [
                'crushing_chest_pain',
                'radiating_pain',
                'shortness_of_breath'
            ],
            'bleeding': [
                'uncontrolled_bleeding',
                'fainting'
            ],
            'pregnancy': [
                'vaginal_bleeding',
                'severe_abdominal_pain'
            ]
        }

    def get_next_question(
        self,
        complaint_group: str,
        age_group: str,
        current_indicators: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Get the next appropriate question based on current context
        
        Args:
            complaint_group: The classified complaint group
            age_group: Patient's age group
            current_indicators: Already collected symptom indicators
            
        Returns:
            Dictionary with question and metadata
        """
        
        # Normalize inputs
        complaint_group = complaint_group or 'other'
        age_group = age_group or 'adult'
        
        # Get the question tree for this complaint group
        tree = self.QUESTION_TREES.get(complaint_group, self.QUESTION_TREES['other'])
        
        # Check if we already have enough information
        if self.has_sufficient_information(complaint_group, age_group, current_indicators):
            return {
                'has_question': False,
                'question': None,
                'reason': 'sufficient_information'
            }
        
        # Check for red flags that should trigger immediate completion
        red_flags_detected = self._check_for_red_flags(complaint_group, current_indicators)
        if red_flags_detected:
            return {
                'has_question': False,
                'question': None,
                'reason': 'red_flags_detected',
                'red_flags': red_flags_detected
            }
        
        # Get age-specific questions
        age_questions = tree.get('age_specific', {})
        
        # Try to get questions for this specific age group
        questions = age_questions.get(age_group, [])
        
        # If no questions for this age, try parent groups
        if not questions:
            questions = self._get_fallback_questions(age_group, age_questions)
        
        # If still no questions, use default
        if not questions:
            questions = age_questions.get('default', [
                "Can you tell me more about your symptoms?",
                "How severe are your symptoms?",
                "How long have you had these symptoms?"
            ])
        
        # Filter out already answered questions based on indicators
        unanswered = self._filter_unanswered(questions, current_indicators, tree)
        
        if unanswered:
            question = unanswered[0]
            return {
                'has_question': True,
                'question': question,
                'question_type': self._get_question_type(question),
                'expected_response': 'text',
                'mapping': self._get_mapping_for_question(question, tree),
                'remaining_questions': len(unanswered) - 1
            }
        else:
            # If all questions answered, we have enough info
            return {
                'has_question': False,
                'question': None,
                'reason': 'all_questions_answered'
            }
    
    def _check_for_red_flags(
        self,
        complaint_group: str,
        indicators: Dict[str, bool]
    ) -> List[str]:
        """Check if any red flags are present in indicators"""
        triggers = self.RED_FLAG_TRIGGERS.get(complaint_group, [])
        detected = []
        
        for trigger in triggers:
            if indicators.get(trigger, False):
                detected.append(trigger)
        
        return detected
    
    def _get_fallback_questions(
        self,
        age_group: str,
        age_questions: Dict[str, List[str]]
    ) -> List[str]:
        """Get questions from a parent age group if specific group not found"""
        
        # Age group hierarchy (older groups can use younger group questions)
        hierarchy = {
            'newborn': ['infant'],
            'infant': ['child_1_5'],
            'child_1_5': ['child_6_12'],
            'child_6_12': ['teen'],
            'teen': ['adult'],
            'adult': ['elderly'],
            'elderly': ['adult'],
        }
        
        fallback_groups = hierarchy.get(age_group, [])
        
        for group in fallback_groups:
            if group in age_questions:
                return age_questions[group]
        
        return []
    
    def _filter_unanswered(
        self,
        questions: List[str],
        indicators: Dict[str, bool],
        tree: Dict[str, Any]
    ) -> List[str]:
        """Filter out questions that have already been answered"""
        
        mapping = tree.get('indicator_mapping', {})
        unanswered = []
        
        for question in questions:
            # Check if this question has been answered
            answered = False
            for indicator in mapping.values():
                # Simple heuristic: if indicator exists, question might be answered
                if indicator in indicators:
                    answered = True
                    break
            
            if not answered:
                unanswered.append(question)
        
        return unanswered
    
    def _get_question_type(self, question: str) -> str:
        """Determine the type of question"""
        question_lower = question.lower()
        
        if '?' not in question:
            return 'statement'
        elif question_lower.startswith(('are you', 'is the', 'do you', 'does the', 'have you')):
            return 'yes_no'
        elif question_lower.startswith(('how', 'what', 'where', 'when', 'why', 'which')):
            return 'open_ended'
        elif question_lower.startswith(('can you', 'could you')):
            return 'capability'
        else:
            return 'general'
    
    def _get_mapping_for_question(self, question: str, tree: Dict[str, Any]) -> Optional[str]:
        """Get the indicator mapping for a question"""
        # Simple keyword-based mapping
        question_lower = question.lower()
        mapping = tree.get('indicator_mapping', {})
        
        keyword_map = {
            'breath': 'breathing_difficulty',
            'cough': 'cough',
            'fever': 'fever',
            'pain': 'severe_pain',
            'bleed': 'bleeding',
            'vomit': 'vomiting',
            'diarrhea': 'diarrhea',
            'drink': 'can_drink',
            'feed': 'can_drink',
            'convulsion': 'convulsions',
            'seizure': 'convulsions',
            'confus': 'confusion',
            'conscious': 'unconscious',
            'sleepy': 'lethargic',
            'chest': 'chest_pain',
            'headache': 'headache',
        }
        
        for keyword, indicator in keyword_map.items():
            if keyword in question_lower:
                return indicator
        
        return None
    
    def has_sufficient_information(
        self,
        complaint_group: str,
        age_group: str,
        indicators: Dict[str, bool]
    ) -> bool:
        """Determine if we have enough information to proceed to triage"""
        
        # Core required indicators by complaint group
        core_requirements = {
            'fever': ['fever'],
            'breathing': ['breathing_difficulty', 'cough'],
            'chest_pain': ['chest_pain'],
            'abdominal': ['severe_abdominal_pain', 'vomiting'],
            'headache': ['headache'],
            'injury': ['injury'],
            'bleeding': ['bleeding'],
            'pregnancy': ['pregnancy_concern'],
        }
        
        required = core_requirements.get(complaint_group, [])
        
        # Check if we have at least one core indicator
        has_core = any(indicators.get(req, False) for req in required) if required else True
        
        # Check if we have severity and duration
        has_severity = 'severity' in indicators or any(
            k in indicators for k in ['severe_pain', 'mild_pain', 'moderate_pain']
        )
        
        # For newborns and infants, we need more info
        if age_group in ['newborn', 'infant']:
            pediatric_checks = ['can_drink', 'lethargic', 'convulsions']
            has_pediatric = any(indicators.get(check, False) for check in pediatric_checks)
            return has_core and has_severity and has_pediatric
        
        return has_core and has_severity
    
    def generate_initial_questions(self, complaint_group: str) -> List[str]:
        """Generate initial questions for a complaint group"""
        tree = self.QUESTION_TREES.get(complaint_group, self.QUESTION_TREES['other'])
        return tree.get('initial_questions', [
            "Can you tell me more about your symptoms?"
        ])


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_next_question(
    complaint_group: str,
    age_group: str,
    current_indicators: Dict[str, bool]
) -> Dict[str, Any]:
    """Convenience function to get next question"""
    tool = AdaptiveQuestioningTool()
    return tool.get_next_question(complaint_group, age_group, current_indicators)


def has_sufficient_info(
    complaint_group: str,
    age_group: str,
    indicators: Dict[str, bool]
) -> bool:
    """Convenience function to check if we have enough info"""
    tool = AdaptiveQuestioningTool()
    return tool.has_sufficient_information(complaint_group, age_group, indicators)