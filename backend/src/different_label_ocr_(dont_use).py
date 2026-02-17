"""
Alcohol Label Verification System
Uses PaddleOCR for text extraction with OpenAI fallback for low-confidence cases
"""

import cv2
import numpy as np
import json
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional
import os
import logging

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
logging.disable(logging.WARNING)

from paddleocr import PaddleOCR
from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize PaddleOCR (CPU optimized)
ocr = PaddleOCR(
    lang='en',
    device='cpu',
    use_textline_orientation=True,
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,

)


def verify_label(image_bytes: bytes, app_data: dict) -> dict:
    """
    Main verification function - compares label image against application data
    
    Args:
        image_bytes: Image file as bytes
        app_data: Dict with keys: brandName, classType, alcoholContent, netContents,
                 producerName, countryOfOrigin, governmentWarning
    
    Returns:
        Dict with verification results
    """
    # Decode image
    img = decode_image(image_bytes)
    
    # Run OCR
    ocr_result = ocr.predict(img)
    
    # Extract and classify fields from OCR
    extracted, confidence = classify_label_fields(ocr_result, img.shape)
    
    # If confidence is low, use OpenAI for better classification
    if confidence < 0.7:
        print(f"Low confidence ({confidence:.2f}), falling back to OpenAI...")
        extracted = classify_with_openai(image_bytes, ocr_result)
    
    # Compare extracted data with application data
    fields = compare_all_fields(extracted, app_data)
    
    # Determine overall status
    has_fails = any(f['status'] == 'fail' for f in fields)
    has_warnings = any(f['status'] == 'warning' for f in fields)
    
    if has_fails:
        overall_status = 'rejected'
        summary = 'One or more required fields failed verification.'
    elif has_warnings:
        overall_status = 'review'
        summary = 'All fields present but some require manual review.'
    else:
        overall_status = 'approved'
        summary = 'All fields verified successfully.'
    
    return {
        'overallStatus': overall_status,
        'summary': summary,
        'fields': fields,
        'method': 'openai' if confidence < 0.7 else 'paddleocr'
    }


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Convert bytes to OpenCV image"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Resize if too large (for speed)
    height, width = img.shape[:2]
    if width > 1536:
        scale = 1536 / width
        img = cv2.resize(img, None, fx=scale, fy=scale)
    
    return img


def classify_label_fields(ocr_result: List, img_shape: Tuple) -> Tuple[Dict, float]:
    """
    Classify OCR results into structured fields using heuristics
    
    Returns:
        Tuple of (extracted_fields_dict, confidence_score)
    """
    if not ocr_result or not ocr_result[0]:
        return {}, 0.0
    
    rec_texts = ocr_result[0]['rec_texts']
    rec_polys = ocr_result[0]['rec_polys']
    rec_scores = ocr_result[0]['rec_scores']
    
    img_height, img_width = img_shape[:2]
    
    # Create structured elements with positions
    elements = []
    for text, poly, score in zip(rec_texts, rec_polys, rec_scores):
        y_center = (poly[0][1] + poly[2][1]) / 2
        x_center = (poly[0][0] + poly[2][0]) / 2
        height = poly[2][1] - poly[0][1]
        
        elements.append({
            'text': text,
            'y': y_center,
            'x': x_center,
            'height': height,
            'score': score,
            'y_norm': y_center / img_height,  # Normalized position
            'x_norm': x_center / img_width
        })
    
    # Extract each field
    brand = extract_brand_name(elements, img_height)
    class_type = extract_class_type(rec_texts)
    alcohol = extract_alcohol_content(rec_texts)
    net_contents = extract_net_contents(rec_texts)
    producer = extract_producer(rec_texts, elements)
    warning = extract_government_warning(rec_texts)
    country = extract_country(rec_texts)
    
    # Calculate confidence score based on how many fields we found
    extracted = {
        'brandName': brand,
        'classType': class_type,
        'alcoholContent': alcohol,
        'netContents': net_contents,
        'producerName': producer,
        'countryOfOrigin': country,
        'governmentWarning': warning
    }
    
    # Confidence based on:
    # 1. OCR scores
    # 2. Number of fields successfully extracted
    # 3. Presence of key indicators (GOVERNMENT WARNING, %, mL, etc.)
    avg_ocr_score = np.mean(rec_scores)
    fields_found = sum(1 for v in extracted.values() if v)
    fields_confidence = fields_found / 7.0  # 7 total fields
    
    # Boost confidence if critical fields found
    has_warning = 'government warning' in warning.lower() if warning else False
    has_alcohol = '%' in alcohol or 'proof' in alcohol.lower() if alcohol else False
    critical_bonus = 0.1 if (has_warning and has_alcohol) else 0
    
    overall_confidence = (avg_ocr_score * 0.4 + fields_confidence * 0.5 + critical_bonus)
    
    return extracted, overall_confidence


def extract_brand_name(elements: List[Dict], img_height: int) -> str:
    """Extract brand name - usually large text in top 40% of label"""
    # Filter to top portion
    top_elements = [e for e in elements if e['y_norm'] < 0.4]
    
    if not top_elements:
        return ""
    
    # Exclude common non-brand words
    exclude_words = ['distilled', 'bottled', 'by:', 'and', 'by']
    candidates = [
        e for e in top_elements 
        if e['text'].lower() not in exclude_words 
        and len(e['text']) >= 2
        and not e['text'].isdigit()
    ]
    
    # Look for largest text in top section (brands are often biggest)
    if candidates:
        largest = max(candidates, key=lambda e: e['height'])
        return largest['text']
    
    return ""


def extract_class_type(rec_texts: List[str]) -> str:
    """Extract spirit class/type (e.g., 'Straight Rye Whisky')"""
    # Spirit type keywords
    spirit_keywords = [
        'whisky', 'whiskey', 'bourbon', 'vodka', 'rum', 
        'gin', 'tequila', 'brandy', 'rye', 'scotch', 'cognac'
    ]
    
    # Find spirit keyword indices
    spirit_indices = []
    for i, text in enumerate(rec_texts):
        if text.lower() in spirit_keywords:
            spirit_indices.append(i)
    
    if not spirit_indices:
        return ""
    
    # Build class/type from surrounding context
    # Typically: [DESCRIPTOR] [DESCRIPTOR] [SPIRIT_TYPE]
    # e.g., "SINGLE BARREL STRAIGHT RYE WHISKY"
    result_words = []
    for idx in spirit_indices:
        # Get 3 words before and the spirit word
        start = max(0, idx - 3)
        end = idx + 1
        
        for i in range(start, end):
            word = rec_texts[i]
            # Include descriptors like STRAIGHT, SINGLE, BARREL, AGED, etc.
            if (word.lower() in spirit_keywords or 
                word.lower() in ['straight', 'single', 'barrel', 'double', 'aged', 'small', 'batch']):
                if word not in result_words:
                    result_words.append(word)
    
    return ' '.join(result_words)


def extract_alcohol_content(rec_texts: List[str]) -> str:
    """Extract alcohol percentage (e.g., '45% ALC/VOL' or '90 PROOF')"""
    full_text = ' '.join(rec_texts)
    
    # Patterns for alcohol content
    patterns = [
        r'\d+\.?\d*%\s*(?:ALC[/.]?VOL|ABV)',
        r'\d+\.?\d*%\s*(?:alc[/.]?vol|abv)',
        r'\d+\.?\d*\s*(?:PROOF|proof)',
        r'\d+\.?\d*%'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            # Try to get fuller context
            start = max(0, match.start() - 5)
            end = min(len(full_text), match.end() + 15)
            context = full_text[start:end].strip()
            
            # Extract just the relevant part
            if 'ALC' in context.upper() or 'PROOF' in context.upper():
                return match.group(0)
    
    return ""


def extract_net_contents(rec_texts: List[str]) -> str:
    """Extract volume (e.g., '750 ML')"""
    # Look for patterns like "750 ML", "1 L", "750ML"
    for i, text in enumerate(rec_texts):
        # Check current element
        if re.search(r'\d+\s*(?:ML|ml|L|mL|liter)', text, re.IGNORECASE):
            return text
    
    # Check for split elements: "750" and "ML" separate
    for i in range(len(rec_texts) - 1):
        if (re.match(r'^\d+$', rec_texts[i]) and 
            re.match(r'^(?:ML|ml|L|mL)$', rec_texts[i+1], re.IGNORECASE)):
            return f"{rec_texts[i]} {rec_texts[i+1]}"
    
    return ""


def extract_producer(rec_texts: List[str], elements: List[Dict]) -> str:
    """Extract producer name and address"""
    # Look for trigger phrases
    trigger_phrases = ['distilled and bottled by', 'bottled by', 'produced by', 'distilled by']
    
    trigger_idx = None
    full_text_lower = ' '.join(rec_texts).lower()
    
    for phrase in trigger_phrases:
        if phrase in full_text_lower:
            # Find approximately where this starts
            for i, text in enumerate(rec_texts):
                if text.lower() in phrase.split():
                    trigger_idx = i
                    break
            break
    
    if trigger_idx is None:
        # Fallback: look for "DISTILLERY" or location patterns
        for i, text in enumerate(rec_texts):
            if 'distillery' in text.lower():
                # Get this word and next 1-2 (likely location)
                parts = rec_texts[i:min(i+3, len(rec_texts))]
                return ' '.join(parts)
        return ""
    
    # Collect producer info after trigger
    producer_parts = []
    for i in range(trigger_idx, min(trigger_idx + 6, len(rec_texts))):
        text = rec_texts[i]
        
        # Stop at certain keywords that indicate we've left producer section
        stop_words = ['single', 'barrel', 'straight', 'aged', 'whisky', 'whiskey', 
                      'rye', 'bourbon', 'government', 'warning']
        if text.lower() in stop_words:
            break
        
        producer_parts.append(text)
    
    return ' '.join(producer_parts)


def extract_government_warning(rec_texts: List[str]) -> str:
    """Extract full government warning statement"""
    # Find starting point
    start_idx = None
    for i, text in enumerate(rec_texts):
        if 'government' in text.lower():
            start_idx = i
            break
    
    if start_idx is None:
        return ""
    
    # Collect all warning text
    warning_parts = []
    # Indicators that we've reached the end of warning
    stop_indicators = ['back', 'label', 'brand', 'barcode', '|||||']
    
    for i in range(start_idx, len(rec_texts)):
        text = rec_texts[i]
        
        # Stop if we hit non-warning content
        if any(stop in text.lower() for stop in stop_indicators):
            break
        
        # Stop if we see a long barcode-like string
        if len(text) > 10 and text.replace('|', '').replace('"', '').isdigit():
            break
        
        warning_parts.append(text)
    
    return ' '.join(warning_parts)


def extract_country(rec_texts: List[str]) -> str:
    """Extract country of origin if present"""
    # Common country indicators
    countries = ['USA', 'United States', 'Mexico', 'Scotland', 'Ireland', 
                 'Canada', 'France', 'Japan', 'Kentucky', 'Tennessee']
    
    full_text = ' '.join(rec_texts)
    for country in countries:
        if country.lower() in full_text.lower():
            return country
    
    # Look for state names (often used for US products)
    us_states = ['KY', 'TN', 'CA', 'Kentucky', 'Tennessee', 'California']
    for state in us_states:
        if state in rec_texts or state.upper() in rec_texts:
            return 'USA'
    
    return ""


def classify_with_openai(image_bytes: bytes, ocr_result: List) -> Dict[str, str]:
    """
    Fallback to OpenAI for classification when PaddleOCR confidence is low
    """
    # Get the text extracted by OCR
    rec_texts = ocr_result[0]['rec_texts'] if ocr_result and ocr_result[0] else []
    all_text = ' '.join(rec_texts)
    
    # Convert image to base64
    import base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = f"""You are analyzing an alcohol beverage label. Here is the text extracted by OCR:

{all_text}

Please classify this text into the following fields:
1. Brand Name (the product brand, usually prominent)
2. Class/Type (e.g., "Straight Rye Whisky", "Single Barrel Bourbon")
3. Alcohol Content (e.g., "45% ALC/VOL", "90 Proof")
4. Net Contents (e.g., "750 ML")
5. Producer Name and Address (who bottled/distilled it and where)
6. Country of Origin (if mentioned)
7. Government Warning Statement (the full warning text)

Respond ONLY with valid JSON in this format:
{{
  "brandName": "...",
  "classType": "...",
  "alcoholContent": "...",
  "netContents": "...",
  "producerName": "...",
  "countryOfOrigin": "...",
  "governmentWarning": "..."
}}

If a field is not found, use an empty string."""

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=800,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{base64_image}',
                                'detail': 'high'
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }
            ]
        )
        
        result_text = response.choices[0].message.content
        # Remove markdown code fences if present
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(result_text)
        
        return result
        
    except Exception as e:
        print(f"OpenAI classification error: {e}")
        # Return empty dict on error
        return {
            'brandName': '',
            'classType': '',
            'alcoholContent': '',
            'netContents': '',
            'producerName': '',
            'countryOfOrigin': '',
            'governmentWarning': ''
        }


def compare_all_fields(extracted: Dict, expected: Dict) -> List[Dict]:
    """Compare all extracted fields against expected values"""
    field_mapping = [
        ('brandName', 'Brand Name'),
        ('classType', 'Class/Type'),
        ('alcoholContent', 'Alcohol Content'),
        ('netContents', 'Net Contents'),
        ('producerName', 'Producer Name & Address'),
        ('countryOfOrigin', 'Country of Origin'),
        ('governmentWarning', 'Government Warning')
    ]
    
    results = []
    for key, label in field_mapping:
        extracted_value = extracted.get(key, '')
        expected_value = expected.get(key, '')
        
        status, note = compare_field(key, extracted_value, expected_value)
        
        results.append({
            'field': label,
            'extracted': extracted_value,
            'expected': expected_value,
            'status': status,
            'note': note
        })
    
    return results


def compare_field(field_key: str, extracted: str, expected: str) -> Tuple[str, Optional[str]]:
    """
    Compare a single field and return (status, note)
    Status: 'pass', 'fail', 'warning'
    """
    # Handle empty cases
    if not extracted:
        if not expected:
            return ('pass', None)
        return ('fail', 'Field not found on label')
    
    if not expected:
        return ('pass', None)
    
    # Normalize for comparison
    ext_norm = extracted.lower().strip()
    exp_norm = expected.lower().strip()
    
    # Exact match
    if ext_norm == exp_norm:
        return ('pass', None)
    
    # Government warning requires EXACT match (including capitalization)
    if field_key == 'governmentWarning':
        # Check if "GOVERNMENT WARNING:" is in all caps
        if 'GOVERNMENT WARNING:' not in extracted:
            if 'government warning:' in extracted.lower():
                return ('fail', 'GOVERNMENT WARNING: must be in all capitals')
        
        # Check content match
        if extracted.strip() != expected.strip():
            return ('fail', 'Government warning text must match exactly')
        
        return ('pass', None)
    
    # For brand name and producer: use fuzzy matching (Dave's case)
    if field_key in ['brandName', 'producerName']:
        similarity = SequenceMatcher(None, ext_norm, exp_norm).ratio()
        if similarity > 0.85:
            return ('warning', f'Minor difference: "{extracted}" vs "{expected}"')
        elif similarity > 0.6:
            return ('warning', f'Possible match but significant difference')
        else:
            return ('fail', f'Does not match: found "{extracted}", expected "{expected}"')
    
    # For alcohol content: check if numbers match
    if field_key == 'alcoholContent':
        ext_nums = re.findall(r'\d+\.?\d*', extracted)
        exp_nums = re.findall(r'\d+\.?\d*', expected)
        
        if ext_nums and exp_nums and ext_nums[0] == exp_nums[0]:
            # Numbers match, minor format difference okay
            if similarity := SequenceMatcher(None, ext_norm, exp_norm).ratio() > 0.7:
                return ('warning', 'Percentage matches but format differs slightly')
        
        return ('fail', f'Alcohol content mismatch: "{extracted}" vs "{expected}"')
    
    # For net contents: check if numbers match
    if field_key == 'netContents':
        ext_nums = re.findall(r'\d+', extracted)
        exp_nums = re.findall(r'\d+', expected)
        
        if ext_nums and exp_nums and ext_nums[0] == exp_nums[0]:
            return ('pass', None)
        
        return ('fail', f'Volume mismatch: "{extracted}" vs "{expected}"')
    
    # General fuzzy matching for other fields
    similarity = SequenceMatcher(None, ext_norm, exp_norm).ratio()
    if similarity > 0.8:
        return ('warning', 'Close match but not exact')
    else:
        return ('fail', f'Mismatch: "{extracted}" vs "{expected}"')


# Example usage
if __name__ == "__main__":
    # Test with sample data
    with open('/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1_chatgpt-upscale.png', 'rb') as f:
        image_bytes = f.read()
    
    app_data = {
        'brandName': 'ABC',
        'classType': 'Straight Rye Whisky',
        'alcoholContent': '45% ALC/VOL',
        'netContents': '750 ML',
        'producerName': 'ABC DISTILLERY FREDERICK, MD',
        'countryOfOrigin': 'USA',
        'governmentWarning': 'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.'
    }
    
    result = verify_label(image_bytes, app_data)
    print(json.dumps(result, indent=2))