"""Prompt templates for all task types."""


def get_labeling_prompt(task_type: str, text_content: str, critic_feedback: str = "") -> str:
    feedback_block = ""
    if critic_feedback:
        feedback_block = f"""
PREVIOUS ATTEMPT FEEDBACK (incorporate this into your new label):
{critic_feedback}
"""

    prompts = {
        "ner": f"""You are a Named Entity Recognition (NER) expert.
{feedback_block}
Label the primary named entity type in the following text.
Choose one of: PERSON, ORGANIZATION, LOCATION, DATE, PRODUCT, EVENT, OTHER

Text: {text_content}

Return ONLY valid JSON: {{"label": "ENTITY_TYPE", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "sentiment": f"""You are a sentiment analysis expert.
{feedback_block}
Classify the sentiment of the following text.
Choose one of: POSITIVE, NEGATIVE, NEUTRAL, MIXED

Text: {text_content}

Return ONLY valid JSON: {{"label": "SENTIMENT", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "summarization": f"""You are a text summarization expert.
{feedback_block}
Create a concise label/category for the following text based on its main topic.
Choose one of: TECHNICAL, SCIENTIFIC, NEWS, OPINION, NARRATIVE, INSTRUCTIONAL, OTHER

Text: {text_content}

Return ONLY valid JSON: {{"label": "CATEGORY", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "object_detection": f"""You are a computer vision expert describing image content.
{feedback_block}
Label the primary object or scene type described.
Choose one of: PERSON, VEHICLE, ANIMAL, BUILDING, FOOD, NATURE, OBJECT, SCENE

Description/Text: {text_content}

Return ONLY valid JSON: {{"label": "CATEGORY", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "ocr": f"""You are an OCR classification expert.
{feedback_block}
Classify the type of document or text in the following content.
Choose one of: HANDWRITTEN, PRINTED, MIXED, FORM, TABLE, RECEIPT, LABEL, OTHER

Text: {text_content}

Return ONLY valid JSON: {{"label": "DOCUMENT_TYPE", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "visual_qa": f"""You are a visual question answering expert.
{feedback_block}
Answer the question based on the provided context.

Context: {text_content}

Return ONLY valid JSON: {{"label": "YOUR_ANSWER", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "captioning": f"""You are an image captioning expert.
{feedback_block}
Generate a concise label/category for the content described.
Choose one of: PORTRAIT, LANDSCAPE, ACTION, GROUP, PRODUCT, ABSTRACT, DOCUMENTARY

Content: {text_content}

Return ONLY valid JSON: {{"label": "CAPTION_TYPE", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",

        "grounded_description": f"""You are a visual grounding expert.
{feedback_block}
Classify the description type and identify key regions.

Content: {text_content}

Return ONLY valid JSON: {{"label": "DESCRIPTION_TYPE", "confidence": 85, "reasoning": "brief explanation", "bounding_boxes": []}}""",
    }

    return prompts.get(task_type.lower(), prompts["sentiment"])


def get_critic_prompt(task_type: str, original_input: str, labeler_output: dict, rubric: dict) -> str:
    rubric_text = ""
    if rubric:
        criteria = rubric.get("criteria", [])
        rubric_text = "Evaluation criteria:\n" + "\n".join(f"- {c}" for c in criteria)

    return f"""You are a label quality critic. Evaluate whether this label is correct.
Do NOT re-label. Only judge correctness.

Task type: {task_type}
Original input: {original_input}
Proposed label: {labeler_output.get('label', '')}
Reasoning: {labeler_output.get('reasoning', '')}
{rubric_text}

Return ONLY valid JSON: {{"is_correct": true/false, "confidence_score": 85, "critique": "specific feedback if incorrect, or 'Label is correct' if correct"}}"""
