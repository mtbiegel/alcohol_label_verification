import os
import base64
import json
import re
from openai import OpenAI
from rapidfuzz import fuzz
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

GOV_WARNING_STR = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

GOV_WARNING_MAIN_STR = (
    "(1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

def extract_fields_with_vision(image_bytes, expected_values):
    """Use OpenAI Vision API to extract fields from label image"""

    expected_brand_name = expected_values["brand_name"]
    expected_class_type = expected_values["class_type"]
    expected_alcohol_content = expected_values["alcohol_content"]
    expected_net_content = expected_values["net_contents"]
    
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = (f"""You are a TTB (Alcohol and Tobacco Tax and Trade Bureau) label compliance expert.

Extract the following information from this alcohol beverage label and determine if the values match the expected values:

1. **Brand Name** - The main product brand (usually the largest text). The expected value is {expected_brand_name}. Does it match? Populate json accordingly with the instructions later in the message.
2. **Class/Type** - The beverage category (e.g., "Straight Rye Whisky", "India Pale Ale", "Single Barrel Bourbon"). The expected value is {expected_class_type}. Does it match? Populate json accordingly with the instructions later in the message.
3. **Alcohol Content** - The ABV percentage (e.g., "45% ALC/VOL", "5.5% ABV"). The expected value is {expected_alcohol_content}. Does it match? Populate json accordingly with the instructions later in the message.
4. **Net Contents** - The volume (e.g., "750 ML", "12 FL OZ"). The expected value is {expected_net_content}. Does it match? Populate json accordingly with the instructions later in the message.
5. **Government Warning** - Check if present and if "GOVERNMENT WARNING:" is in all caps. The expected value is {GOV_WARNING_STR}. Does it match? Populate json accordingly with the instructions later in the message.

Ignore captilization and adjusted for small discrepancies between the classified and expected values. 
However, the government warning label must have the EXACT wording and capitalization as the expected value, but the words can be stacked or rotated",
If the government warning is present in all caps as "GOVERNMENT WARNING:" and the main body of text as follows {GOV_WARNING_MAIN_STR} is present, then set "government_warning_matches" to true
Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "brand_name": "exact text from label",
  "brand_name_matches": "true/false if brand name matches",
  "class_type": "exact text from label",
  "class_type_matches": "true/false if class type matches",
  "alcohol_content": "exact text from label",
  "alcohol_content_matches": "true/false if alcohol content matches expected value",
  "net_contents": "exact text from label",
  "net_contents_matches": "true/false if net contents matches expected value",
  "government_warning_present": "true/false",
  "government_warning_all_caps": "true/false",
  "government_warning_text": "full text if present, empty string if not"
  "government_warning_matches": "true/false if the government_warning_all_caps is set to true and government_warning_text equals {GOV_WARNING_MAIN_STR},
}}

If a field is not visible on the label, use an empty string.""")

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=800,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{base64_image}',
                            'detail': 'high'
                        }
                    },
                    {'type': 'text', 'text': prompt}
                ]
            }]
        )
        
        result_text = response.choices[0].message.content
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(result_text)
        return extracted
        
    except Exception as e:
        print(f"Vision API error: {e}")
        return {
            'brand_name': '',
            'class_type': '',
            'alcohol_content': '',
            'net_contents': '',
            'government_warning_present': False,
            'government_warning_all_caps': False,
            'government_warning_text': ''
        }


def compare_brand_name(extracted: str, expected: str) -> tuple:
    if not extracted:
        return ('fail', 'Brand name not found on label')
    if not expected:
        return ('pass', None)
    
    ext_norm = extracted.lower().strip()
    exp_norm = expected.lower().strip()
    
    if ext_norm == exp_norm:
        return ('pass', None)
    
    len_ratio = min(len(ext_norm), len(exp_norm)) / max(len(ext_norm), len(exp_norm))
    if len_ratio < 0.85:
        return ('fail', f'Brand name mismatch: found "{extracted}", expected "{expected}"')
    
    similarity = fuzz.ratio(ext_norm, exp_norm)
    
    if similarity >= 90:
        return ('warning', f'Minor difference (similarity {round(similarity, 1)}%)')
    
    if similarity >= 75:
        return ('warning', f'Possible match but significant difference (similarity {round(similarity, 1)}%)')
    
    return ('fail', f'Brand name mismatch')


def compare_class_type(extracted: str, expected: str) -> tuple:
    if not extracted:
        return ('fail', 'Class/type not found on label')
    if not expected:
        return ('pass', None)
    
    ext_norm = extracted.lower().strip()
    exp_norm = expected.lower().strip()
    
    if ext_norm == exp_norm:
        return ('pass', None)
    
    if ext_norm in exp_norm or exp_norm in ext_norm:
        return ('warning', f'Partial match — verify full class/type on label')
    
    similarity = fuzz.ratio(ext_norm, exp_norm)
    partial = fuzz.partial_ratio(ext_norm, exp_norm)
    best = max(similarity, partial)
    
    if best >= 80:
        return ('warning', f'Close match but difference detected (similarity: {round(best, 1)}%)')
    
    return ('fail', f'Class/type mismatch')


def compare_alcohol_content(extracted: str, expected: str) -> tuple:
    if not extracted:
        return ('fail', 'Alcohol content not found on label')
    if not expected:
        return ('fail', 'Expected alcohol content is missing from application data')
    
    ext_nums = re.findall(r'\d+\.?\d*', extracted)
    exp_nums = re.findall(r'\d+\.?\d*', expected)
    
    if not ext_nums or not exp_nums:
        return ('fail', f'Could not parse alcohol content')
    
    ext_num = float(ext_nums[0])
    exp_num = float(exp_nums[0])
    
    if ext_num == exp_num:
        ext_has_proof = 'proof' in extracted.lower()
        exp_has_proof = 'proof' in expected.lower()
        
        if ext_has_proof != exp_has_proof:
            return ('warning', f'Percentage matches but format differs')
        
        return ('pass', None)
    
    if abs(ext_num - exp_num) <= 0.5:
        return ('warning', f'Minor difference detected')
    
    return ('fail', f'Alcohol content mismatch')


def compare_net_contents(extracted: str, expected: str) -> tuple:
    if not extracted:
        return ('fail', 'Net contents not found on label')
    if not expected:
        return ('pass', None)
    
    ext_nums = re.findall(r'\d+\.?\d*', extracted)
    exp_nums = re.findall(r'\d+\.?\d*', expected)
    
    if not ext_nums or not exp_nums:
        return ('fail', f'Could not parse net contents')
    
    if ext_nums[0] != exp_nums[0]:
        return ('fail', f'Volume mismatch')
    
    ext_unit = re.sub(r'[\d\.\s]', '', extracted).strip().lower()
    exp_unit = re.sub(r'[\d\.\s]', '', expected).strip().lower()
    
    if ext_unit != exp_unit:
        return ('fail', f'Unit mismatch')
    
    return ('pass', None)


def check_government_warning(warning_present: bool, warning_all_caps: bool, warning_text: str, warning_matches: list) -> tuple:

    if not warning_present:
        return ('fail', 'Government warning statement not found on label')
    
    if not warning_all_caps:
        return ('fail', '"GOVERNMENT WARNING:" must be in all capitals')
        
    # Overrule algorithm-based classification if all of these are true
    if warning_all_caps and warning_text == GOV_WARNING_MAIN_STR and warning_matches:
        print("AI SAYS GOV WARNING PASSES")
        return ('pass', None) 

    # Fuzzy match the actual warning text
    if warning_text:
        expected = GOV_WARNING_STR.upper()
        extracted = warning_text.upper()
        
        similarity = fuzz.ratio(extracted, expected)
        
        if similarity == 100:
            return ('pass', None)
        
        if similarity >= 95:
            return ('warning', f'Warning statement is very close but not exact (similarity: {round(similarity, 1)}%). May be an OCR artifact')
        
        if similarity >= 80:
            return ('warning', f'Warning statement has notable differences (similarity: {round(similarity, 1)}%). Manual review required')
        
        return ('fail', f'Warning statement does not match required text (similarity: {round(similarity, 1)}%)')
    
    return ('pass', None)


def verify_label(image_bytes, application_data):
    """
    Main verification function using OpenAI Vision API
    
    Args:
        image_bytes: Raw image bytes from frontend upload
        application_data: Dict with expected values from form
    
    Returns:
        Dict with verification results
    """
    
    # Extract fields using Vision API
    extracted = extract_fields_with_vision(image_bytes, application_data)
    print()
    print("EXTRACTED:")
    print(json.dumps(extracted, indent=2))
    print()
    
    # Compare each field
    brand_status, brand_note = compare_brand_name(
        extracted.get('brand_name', ''),
        application_data.get('brand_name', '')
    )
    
    class_status, class_note = compare_class_type(
        extracted.get('class_type', ''),
        application_data.get('class_type', '')
    )
    
    alcohol_status, alcohol_note = compare_alcohol_content(
        extracted.get('alcohol_content', ''),
        application_data.get('alcohol_content', '')
    )
    
    contents_status, contents_note = compare_net_contents(
        extracted.get('net_contents', ''),
        f"{application_data.get('net_contents_amount', '')} {application_data.get('net_contents_unit', '')}".strip()
    )
    
    warning_status, warning_note = check_government_warning(
        extracted.get('government_warning_present', False),
        extracted.get('government_warning_all_caps', False),
        extracted.get('government_warning_text', ''),
        extracted.get('government_warning_matches', False)
    )
    
    # Build response
    fields = [
        {
            'field': 'Brand Name',
            'extracted': extracted.get('brand_name', ''),
            'expected': application_data.get('brand_name', ''),
            'status': brand_status,
            'note': brand_note
        },
        {
            'field': 'Class/Type',
            'extracted': extracted.get('class_type', ''),
            'expected': application_data.get('class_type', ''),
            'status': class_status,
            'note': class_note
        },
        {
            'field': 'Alcohol Content',
            'extracted': extracted.get('alcohol_content', ''),
            'expected': application_data.get('alcohol_content', ''),
            'status': alcohol_status,
            'note': alcohol_note
        },
        {
            'field': 'Net Contents',
            'extracted': extracted.get('net_contents', ''),
            'expected': f"{application_data.get('net_contents_amount', '')} {application_data.get('net_contents_unit', '')}".strip(),
            'status': contents_status,
            'note': contents_note
        },
        {
            'field': 'Government Warning',
            'extracted': 'GOVERNMENT WARNING: present' if extracted.get('government_warning_present') else 'Not found or incorrect',
            'expected': 'GOVERNMENT WARNING: (standard text)',
            'status': warning_status,
            'note': warning_note
        },
    ]
    
    has_fails = any(f['status'] == 'fail' for f in fields)
    has_warnings = any(f['status'] == 'warning' for f in fields)
    
    overall = 'rejected' if has_fails else ('review' if has_warnings else 'approved')
    
    return {
        'overallStatus': overall,
        'summary': 'All fields verified.' if overall == 'approved' else 'One or more fields require attention.',
        'fields': fields
    }


# Example usage
if __name__ == "__main__":
    # Test with a sample image
    # image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1_chatgpt-upscale.png"
    image_path = "/home/biegemt1/projects/alcohol_label_verification/tests/test_images/1.png"
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    app_data = {
        "brand_name": "ABC",
        "class_type": "Straight Rye Whisky",
        "alcohol_content": "45%",
        "net_contents_amount": "750",
        "net_contents_unit": "mL",
        "net_contents": "750 mL"
    }

    app_data2 = {
        "brand_name": "ABC",
        "class_type": "Whisky",
        "alcohol_content_amount": 45,
        "alcohol_content_format": "%",
        "net_contents_amount": 750,
        "net_contents_unit": "mL",
        "producer_name": "",
        "country_of_origin": "",
        "alcohol_content": "45 %",
        "net_contents": "750 mL"
    }
    
    result = verify_label(image_bytes, app_data2)
    
    print()
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print()