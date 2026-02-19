import asyncio
import os
import base64
import json
import re
from openai import AsyncOpenAI, RateLimitError
from rapidfuzz import fuzz
from dotenv import load_dotenv
import traceback

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

### Constants
BRAND_NAME_STR = "brand_name"
CLASS_TYPE_STR = "class_type"
ALC_CONTENT_STR = "alcohol_content"
NET_CONTENT_STR = "net_contents"
GOV_WARN_TEXT_STR = "government_warning_text"

BRAND_NAME_MATCH_STR = "brand_name_matches"
CLASS_TYPE_NAME_MATCH_STR = "class_type_matches"
ALC_CONTENT_MATCH_STR = "alcohol_content_matches"
NET_CONTENT_MATCH_STR = "net_contents_matches"
GOV_WARN_PRESENT_MATCH_STR = "government_warning_present"
GOV_WARN_CAPS_MATCH_STR = "government_warning_all_caps"
GOV_WARN_MATCH_STR = "government_warning_matches"

DEFAULT_PROMPT_BOOL_STR = "True/False"

COMPARE_BRAND_NAME_MISMATCH_RATIO = 0.85
COMPARE_BRAND_NAME_MORE_SIMILAR_RATIO = 0.90
COMPARE_BRAND_NAME_LESS_SIMILAR_RATIO = 0.75
COMPARE_ALC_CONTENT_DIFF_RATIO = 0.5
CLOSE_BUT_DIFFERENT_SCORE = 80

OVERALL_PASS_SCORE = 100
OVERALL_SIMILAR_SCORE = 95

GOV_WARNING_STR_MAIN_BODY = (
    "(1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

GOV_WARNING_STR = "GOVERNMENT WARNING: " + GOV_WARNING_STR_MAIN_BODY

DEFAULT_EXTRACTED_FIELDS = {
    BRAND_NAME_STR: "",
    BRAND_NAME_MATCH_STR: False,
    CLASS_TYPE_STR: "", 
    CLASS_TYPE_NAME_MATCH_STR: False,
    ALC_CONTENT_STR: "", 
    ALC_CONTENT_MATCH_STR: False,
    NET_CONTENT_STR: "", 
    NET_CONTENT_MATCH_STR: False,
    GOV_WARN_PRESENT_MATCH_STR: False, 
    GOV_WARN_CAPS_MATCH_STR: False,
    GOV_WARN_TEXT_STR: "", 
    GOV_WARN_MATCH_STR: False
}

async def extract_fields_with_vision(image_bytes: bytes, expected_values: dict) -> dict:
    """
        Extracts key alcohol label fields from an image using the OpenAI Vision API and compares them 
        to expected values. Returns a JSON-like dictionary with extracted field values and boolean
        flags indicating matches. Handles missing fields, formatting variations, and propagates rate limit errors.

        Parameter values:
            - image_bytes<byte> = label image from front end.
            - expected_values<dict> = values from user-uploaded application to match against extracted values.
        
        Return value<dict>:
            - A dictionary in proper format with necessary fields to display on front end.
            - Returns empty dictionaries if json.JSONDecodeError or other exceptions occur.
    """

    # Initializing result var
    result_text = "If you see this, a major error has occurred with result_text var"    

    # Initialize expected value vars
    expected_brand_name = expected_values[BRAND_NAME_STR]
    expected_class_type = expected_values[CLASS_TYPE_STR]
    expected_alcohol_content = expected_values[ALC_CONTENT_STR]
    expected_net_content = expected_values[NET_CONTENT_STR]
    
    # Convert image from bytes to encoded values for input into OpenAI Vision API
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # OpenAI Vision API Prompt
    prompt = (f"""You are a U.S. TTB alcohol label compliance expert.

        Extract the following information from this alcohol beverage label and determine if extracted values match the expected values:

        Brand Name → expected: {expected_brand_name}. NOTE: Additional nouns like "Brewery" may not necessarily be part of the brand name.
        Class/Type → expected: {expected_class_type}. NOTE: Additional descriptor words may not necessarily be part of the class/type, but the expected value must be a word in the image.
        Alcohol Content → expected: {expected_alcohol_content}. Make sure to search for this numerical value in image.
        Net Contents → expected: {expected_net_content}. NOTE: Field could vary in wording/formatting and still be correct (i.e "1 Pint, 0.9 FL. OZ." = "1 0.9 Pint Fl oz")

        Government Warning must:
        - MUST contain "GOVERNMENT WARNING:" exact and in ALL CAPS
        - MUST contain exact text: {GOV_WARNING_STR_MAIN_BODY}

        Ignore capitalization differences EXCEPT for "GOVERNMENT WARNING:" which must be exact.

        Respond with ONLY valid JSON:

        {{
            "{BRAND_NAME_STR}": "",
            "{BRAND_NAME_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{CLASS_TYPE_STR}": "",
            "{CLASS_TYPE_NAME_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{ALC_CONTENT_STR}": "",
            "{ALC_CONTENT_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{NET_CONTENT_STR}": "",
            "{NET_CONTENT_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{GOV_WARN_PRESENT_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{GOV_WARN_CAPS_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR},
            "{GOV_WARN_TEXT_STR}": "",
            "{GOV_WARN_MATCH_STR}": {DEFAULT_PROMPT_BOOL_STR}
        }}

        If a field is not visible, use empty string.
    """)

    # Send prompt and iamge to OpenAI Vision API for processing
    try:
        response = await openai_client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=300,
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
        
        # Process response into standard json format
        result_text = response.choices[0].message.content
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(result_text)
        return extracted

    # Raises error to bubble up to previous function call to handle retry logic if rate limit is reached
    except RateLimitError:
        raise

    # Raises JSON decoding error if result is not in the correct format
    except json.JSONDecodeError as e:
        print(f"Vision API JSON parse error: {e}\nRaw response: {result_text}")
        return DEFAULT_EXTRACTED_FIELDS

    # Raises other errors that are not expected errors
    except Exception as e:
        print(f"Vision API error: {e}")
        traceback.print_exc()
        return DEFAULT_EXTRACTED_FIELDS

def compare_brand_name(extracted: str, matches: bool, expected: str) -> tuple:
    """
        Compares an extracted brand name against the expected value and returns a status and message.
        Returns 'pass', 'fail', or 'warning' based on exact match or similarity thresholds, handling
        missing values and minor differences.

        Parameter values:
            - extracted<str> = brand name extracted from label.
            - matches<bool> = precomputed match flag from automated extraction.
            - expected<str> = expected brand name provided by user or application.
        
        Return value<tuple>:
            - Tuple containing a status string ('pass', 'fail', 'warning') and an optional message
              explaining mismatches or differences.
            - Returns 'fail' with a message if extracted value is missing, or 'pass' if expected value is empty.
    """

    # If extracted empty, no brand name was extracted
    if not extracted:
        return ('fail', 'Brand name not found on label')
    
    # If expected empty, no brand name was extracted
    if not expected:
        return ('fail', "No expected value given")

    # Overrule algorithm-based classification if AI response says it matches
    if matches:
        return ('pass', None) 
    
    # Preprocess extracted and expected strings
    ext_norm = extracted.lower().strip()
    exp_norm = expected.lower().strip()
    
    # Exact match after normalization
    if ext_norm == exp_norm:
        return ('pass', None)
    
    # Calculate relative length ratio to detect major mismatches
    len_ratio = min(len(ext_norm), len(exp_norm)) / max(len(ext_norm), len(exp_norm))
    if len_ratio < COMPARE_BRAND_NAME_MISMATCH_RATIO:
        return ('fail', f'Brand name mismatch: found "{extracted}", expected "{expected}"')
    
    # Compute fuzzy similarity between normalized strings
    similarity = fuzz.ratio(ext_norm, exp_norm)
    
    # Similar enough to pass with minor differences
    if similarity >= COMPARE_BRAND_NAME_MORE_SIMILAR_RATIO:
        return ('warning', f'Minor difference (similarity {round(similarity, 1)}%)')
    
    # Possible match but significant differences detected
    if similarity >= COMPARE_BRAND_NAME_LESS_SIMILAR_RATIO:
        return ('warning', f'Possible match but significant difference (similarity {round(similarity, 1)}%)')
    
    # Default fail case for brand name mismatch
    return ('fail', f'Brand name mismatch')

def compare_class_type(extracted: str, matches: bool, expected: str) -> tuple:
    """
        Compares an extracted class/type against the expected value and returns a status and message.
        Returns 'pass', 'fail', or 'warning' based on exact, partial, or similarity-based matches,
        handling missing values and minor differences.

        Parameter values:
            - extracted<str> = class/type extracted from label.
            - matches<bool> = precomputed match flag from automated extraction.
            - expected<str> = expected class/type provided by user or application.
        
        Return value<tuple>:
            - Tuple containing a status string ('pass', 'fail', 'warning') and an optional message
              explaining mismatches or differences.
            - Returns 'fail' with a message if extracted value is missing, or 'pass' if expected value is empty.
    """

    # If extracted empty, no class/type was extracted
    if not extracted:
        return ('fail', 'Class/type not found on label')
    
    # If expected empty, no brand name was extracted
    if not expected:
        return ('fail', "No expected value given")

    # Overrule algorithm-based classification if AI response says it matches
    if matches:
        return ('pass', None) 
    
    # Preprocess extracted and expected strings for comparison
    ext_norm = extracted.lower().strip()
    exp_norm = expected.lower().strip()
    
    # Exact match after normalization
    if ext_norm == exp_norm:
        return ('pass', None)
    
    # Partial substring match
    if ext_norm in exp_norm or exp_norm in ext_norm:
        return ('warning', f'Partial match — verify full class/type on label')
    
    # Compute fuzzy similarity and partial similarity
    similarity = fuzz.ratio(ext_norm, exp_norm)
    partial = fuzz.partial_ratio(ext_norm, exp_norm)
    best = max(similarity, partial)
    
    # Close match but minor differences detected
    if best >= CLOSE_BUT_DIFFERENT_SCORE:
        return ('warning', f'Close match but difference detected (similarity: {round(best, 1)}%)')
    
    # Default fail case for class/type mismatch
    return ('fail', f'Class/type mismatch')

def compare_alcohol_content(extracted: str, matches: bool, expected: str) -> tuple:
    """
        Compares an extracted alcohol content against the expected value and returns a status and message.
        Returns 'pass', 'fail', or 'warning' based on exact, numeric, or format-based matches, handling
        missing values and minor differences.

        Parameter values:
            - extracted<str> = alcohol content extracted from label.
            - matches<bool> = precomputed match flag from automated extraction.
            - expected<str> = expected alcohol content provided by user or application.
        
        Return value<tuple>:
            - Tuple containing a status string ('pass', 'fail', 'warning') and an optional message
              explaining mismatches or differences.
            - Returns 'fail' with a message if extracted or expected value is missing or cannot be parsed.
    """

    # If extracted empty, no alcohol content was extracted
    if not extracted:
        return ('fail', 'Alcohol content not found on label')
    
    # If expected empty, nothing to compare against
    if not expected:
        return ('fail', 'Expected alcohol content is missing from application data')

    # Overrule algorithm-based classification if AI response says it matches
    if matches:
        return ('pass', None) 
    
    # Extract numeric values from extracted and expected strings
    ext_nums = re.findall(r'\d+\.?\d*', extracted)
    exp_nums = re.findall(r'\d+\.?\d*', expected)
    
    # Fail if numeric values cannot be parsed
    if not ext_nums or not exp_nums:
        return ('fail', f'Could not parse alcohol content')
    
    # Convert first numeric value to float for comparison
    ext_num = float(ext_nums[0])
    exp_num = float(exp_nums[0])
    
    # Exact numeric match
    if ext_num == exp_num:
        # Check for difference in format (e.g., percentage vs proof)
        ext_has_proof = 'proof' in extracted.lower()
        exp_has_proof = 'proof' in expected.lower()
        
        if ext_has_proof != exp_has_proof:
            return ('warning', f'Percentage matches but format differs')
        
        return ('pass', None)
    
    # Minor numeric difference within allowed ratio
    if abs(ext_num - exp_num) <= COMPARE_ALC_CONTENT_DIFF_RATIO:
        return ('warning', f'Minor difference detected')
    
    # Default fail case for alcohol content mismatch
    return ('fail', f'Alcohol content mismatch')

def compare_net_contents(extracted: str, matches: bool, expected: str) -> tuple:
    """
        Compares extracted net contents against the expected value and returns a status and message.
        Returns 'pass' or 'fail' based on numeric and unit matches, handling missing values and
        minor differences.

        Parameter values:
            - extracted<str> = net contents extracted from label.
            - matches<bool> = precomputed match flag from automated extraction.
            - expected<str> = expected net contents provided by user or application.
        
        Return value<tuple>:
            - Tuple containing a status string ('pass', 'fail') and an optional message explaining
              mismatches.
            - Returns 'fail' with a message if extracted or expected value is missing or cannot be parsed.
    """

    # If extracted empty, no net contents were extracted
    if not extracted:
        return ('fail', 'Net contents not found on label')
    
    # If expected empty, nothing to compare against
    if not expected:
        return ('fail', "No expected value given")
    
    # Overrule algorithm-based classification if AI response says it matches
    if matches:
        return ('pass', None) 
    
    # Extract numeric values from extracted and expected strings
    ext_nums = re.findall(r'\d+\.?\d*', extracted)
    exp_nums = re.findall(r'\d+\.?\d*', expected)
    
    # Fail if numeric values cannot be parsed
    if not ext_nums or not exp_nums:
        return ('fail', f'Could not parse net contents')
    
    # Fail if numeric volumes do not match
    if ext_nums[0] != exp_nums[0]:
        return ('fail', f'Volume mismatch')
    
    # Extract units by removing numbers, dots, and whitespace
    ext_unit = re.sub(r'[\d\.\s]', '', extracted).strip().lower()
    exp_unit = re.sub(r'[\d\.\s]', '', expected).strip().lower()
    
    # Fail if units do not match
    if ext_unit != exp_unit:
        return ('fail', f'Unit mismatch')
    
    # Pass if both numeric values and units match
    return ('pass', None)

def check_government_warning(warning_present: bool, warning_all_caps: bool, warning_text: str, warning_matches: list) -> tuple:
    """
        Checks the government warning on a label for presence, capitalization, and text accuracy.
        Returns 'pass', 'fail', or 'warning' based on exact, fuzzy, or partial matches, handling
        missing or incorrectly formatted warnings.

        Parameter values:
            - warning_present<bool> = True if a government warning is detected on the label.
            - warning_all_caps<bool> = True if "GOVERNMENT WARNING:" is in all capitals.
            - warning_text<str> = text of the government warning extracted from the label.
            - warning_matches<list> = list indicating if warning text matches expected segments.
        
        Return value<tuple>:
            - Tuple containing a status string ('pass', 'fail', 'warning') and an optional message
              explaining mismatches or differences.
            - Returns 'fail' if warning is missing, incorrectly capitalized, or text does not match expected.
    """

    # Fail if government warning is not present
    if not warning_present:
        return ('fail', 'Government warning statement not found on label')
    
    # Fail if "GOVERNMENT WARNING:" is not in all capital letters
    if not warning_all_caps:
        return ('fail', '"GOVERNMENT WARNING:" must be in all capitals')
        
    # Overrule algorithm-based classification if all conditions indicate a perfect match
    if warning_all_caps and warning_text == GOV_WARNING_STR_MAIN_BODY and warning_matches:
        return ('pass', None) 

    # Fuzzy match the actual warning text if text is present
    if warning_text:
        expected = GOV_WARNING_STR.upper()
        extracted = warning_text.upper()
        
        # Compute similarity between extracted and expected text
        similarity = fuzz.ratio(extracted, expected)
        
        # Exact match case
        if similarity == OVERALL_PASS_SCORE:
            return ('pass', None)
        
        # Very close match with minor OCR artifacts
        if similarity >= OVERALL_SIMILAR_SCORE:
            return ('warning', f'Warning statement is very close but not exact (similarity: {round(similarity, 1)}%). May be an OCR artifact')
        
        # Notable differences detected; requires manual review
        if similarity >= CLOSE_BUT_DIFFERENT_SCORE:
            return ('warning', f'Warning statement has notable differences (similarity: {round(similarity, 1)}%). Manual review required')
        
        # Default fail case for warning text mismatch
        return ('fail', f'Warning statement does not match required text (similarity: {round(similarity, 1)}%)')
    
    # Pass if no text to compare (fallback)
    return ('pass', None)

async def verify_label(image_bytes, application_data, running_from_main=False) -> dict:
    """
        Main label verification function using base comparison algorithms and the OpenAI Vision API.
        Compares extracted label fields against expected application data and returns detailed results.

        Parameter values:
            - image_bytes<bytes> = raw label image uploaded from frontend.
            - application_data<dict> = expected field values provided by user/application form.
            - running_from_main<bool> = True if called from main thread and requires asyncio.run().
        
        Return value<dict>:
            - Dictionary containing overall status ('approved', 'review', 'rejected'), summary, 
              and per-field verification results including status and notes.
    """

    # Extract fields from image using Vision API
    # Use asyncio.run if called from main, otherwise await the async function
    if running_from_main:    
        extracted = asyncio.run(extract_fields_with_vision(image_bytes, application_data))
    else:
        extracted = await extract_fields_with_vision(image_bytes, application_data)

    # Compare Brand Name field
    brand_status, brand_note = compare_brand_name(
        extracted.get(BRAND_NAME_STR, ''),
        extracted.get('brand_name_matches', False),
        application_data.get(BRAND_NAME_STR, ''),
    )
    
    # Compare Class/Type field
    class_status, class_note = compare_class_type(
        extracted.get(CLASS_TYPE_STR, ''),
        extracted.get(CLASS_TYPE_NAME_MATCH_STR, False),
        application_data.get(CLASS_TYPE_STR, '')
    )
    
    # Compare Alcohol Content field
    alcohol_status, alcohol_note = compare_alcohol_content(
        extracted.get(ALC_CONTENT_STR, ''),
        extracted.get(ALC_CONTENT_MATCH_STR, False),
        application_data.get(ALC_CONTENT_STR, '')
    )

    # Compare Net Contents field
    contents_status, contents_note = compare_net_contents(
        extracted.get(NET_CONTENT_STR, ''),
        extracted.get(NET_CONTENT_MATCH_STR, False),
        application_data.get(NET_CONTENT_STR, '')
    )
    
    # Compare Government Warning field
    warning_status, warning_note = check_government_warning(
        extracted.get(GOV_WARN_PRESENT_MATCH_STR, False),
        extracted.get(GOV_WARN_CAPS_MATCH_STR, False),
        extracted.get(GOV_WARN_TEXT_STR, ''),
        extracted.get(GOV_WARN_MATCH_STR, False)
    )
    
    # Build response for each field
    # Verbosly built for easy-understanding for future developers
    fields = [
        {
            'field': 'Brand Name',
            'extracted': extracted.get(BRAND_NAME_STR, ''),
            'expected': application_data.get(BRAND_NAME_STR, ''),
            'status': brand_status,
            'note': brand_note
        },
        {
            'field': 'Class/Type',
            'extracted': extracted.get(CLASS_TYPE_STR, ''),
            'expected': application_data.get(CLASS_TYPE_STR, ''),
            'status': class_status,
            'note': class_note
        },
        {
            'field': 'Alcohol Content',
            'extracted': extracted.get(ALC_CONTENT_STR, ''),
            'expected': application_data.get(ALC_CONTENT_STR, ''),
            'status': alcohol_status,
            'note': alcohol_note
        },
        {
            'field': 'Net Contents',
            'extracted': extracted.get(NET_CONTENT_STR, ''),
            'expected': f"{application_data.get('net_contents_amount', '')} {application_data.get('net_contents_unit', '')}".strip(),
            'status': contents_status,
            'note': contents_note
        },
        {
            'field': 'Government Warning',
            'extracted': 'GOVERNMENT WARNING: present' if extracted.get(GOV_WARN_PRESENT_MATCH_STR) else 'Not found or incorrect',
            'expected': 'GOVERNMENT WARNING: (standard text)',
            'status': warning_status,
            'note': warning_note
        },
    ]
    
    # Determine overall status based on individual field results
    has_fails = any(f['status'] == 'fail' for f in fields)
    has_warnings = any(f['status'] == 'warning' for f in fields)
    
    overall = 'rejected' if has_fails else ('review' if has_warnings else 'approved')
    
    # Return final verification results including overall status, summary, and per-field details
    return {
        'overallStatus': overall,
        'summary': 'All fields verified.' if overall == 'approved' else 'One or more fields require attention.',
        'fields': fields
    }

if __name__ == "__main__":
    """
        ABOUT main:
            This main function is used for testing values during development
            The intent is to not use it in any deployed setting or aspect
    """
    
    # Test with a sample image
    image_path = "../../tests/test_images/1.png"
    
    # Open File
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Fake test data; simplified
    app_data = {
        BRAND_NAME_STR: "ABC",
        CLASS_TYPE_STR: "Straight Rye Whisky",
        ALC_CONTENT_STR: "45%",
        "net_contents_amount": "750",
        "net_contents_unit": "mL",
        NET_CONTENT_STR: "750 mL"
    }

    # Fake test data; verbose
    app_data2 = {
        BRAND_NAME_STR: "ABC",
        CLASS_TYPE_STR: "Whisky",
        "alcohol_content_amount": 45,
        "alcohol_content_format": "%",
        "net_contents_amount": 750,
        "net_contents_unit": "mL",
        "producer_name": "",
        "country_of_origin": "",
        ALC_CONTENT_STR: "45 %",
        NET_CONTENT_STR: "750 mL"
    }
    
    # Run async verification
    result = asyncio.run(verify_label(image_bytes, app_data2))
    
    # Print results in json format
    print()
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print()