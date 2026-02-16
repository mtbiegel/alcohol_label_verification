import ollama
import base64

def extract_text_moondream(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = ollama.chat(
        model='moondream',
        messages=[{
            'role': 'user',
            'content': 'Transcribe every word and character from this alcohol label exactly as it appears. Include all punctuation, capitalization, and special characters. Return only the raw text.',
            'images': [image_path]
        }]
    )
    return response['message']['content']