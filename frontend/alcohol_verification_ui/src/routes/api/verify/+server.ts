import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import OpenAI from 'openai';
import { OPENAI_API_KEY } from '$env/static/private';
import type { VerificationResult } from '$lib/types';

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

export const POST: RequestHandler = async ({ request }) => {
  try {
    const formData = await request.formData();
    const image = formData.get('image') as File;
    const applicationDataRaw = formData.get('applicationData') as string;

    if (!image || !applicationDataRaw) {
      return json({ message: 'Image and application data are required.' }, { status: 400 });
    }

    const applicationData = JSON.parse(applicationDataRaw);

    const arrayBuffer = await image.arrayBuffer();
    const base64Image = Buffer.from(arrayBuffer).toString('base64');
    const mimeType = image.type || 'image/jpeg';

    const prompt = `You are a TTB (Alcohol and Tobacco Tax and Trade Bureau) label compliance agent.
    
Your job is to compare the information visible on the label image against the application data provided.

APPLICATION DATA:
- Brand Name: ${applicationData.brandName || 'Not provided'}
- Class/Type: ${applicationData.classType || 'Not provided'}
- Alcohol Content: ${applicationData.alcoholContent || 'Not provided'}
- Net Contents: ${applicationData.netContents || 'Not provided'}
- Producer Name & Address: ${applicationData.producerName || 'Not provided'}
- Country of Origin: ${applicationData.countryOfOrigin || 'Not provided'}
- Government Warning: ${applicationData.governmentWarning || 'Not provided'}

VERIFICATION RULES:
1. Brand name: Flag as 'warning' (not 'fail') for minor case differences — use judgment.
2. Government Warning: Must be EXACT. "GOVERNMENT WARNING:" must be in all caps. Any deviation = 'fail'.
3. Alcohol content: Numbers must match exactly. Proof and percentage must be consistent.
4. If a field is not visible on the label, set status to 'fail' with a note that it was not found.

Respond ONLY with valid JSON in this exact format, no markdown, no explanation:
{
  "overallStatus": "approved" | "rejected" | "review",
  "summary": "One sentence summary of the verification result",
  "fields": [
    {
      "field": "Brand Name",
      "extracted": "what you see on the label",
      "expected": "what was in the application",
      "status": "pass" | "fail" | "warning",
      "note": "optional explanation, especially for warnings or failures"
    }
  ]
}

Include a field result for every field in the application data.
Set overallStatus to "approved" only if all fields pass. Set to "rejected" if any field fails. Set to "review" if there are only warnings.`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image_url',
              image_url: {
                url: `data:${mimeType};base64,${base64Image}`,
                detail: 'high'
              }
            },
            {
              type: 'text',
              text: prompt
            }
          ]
        }
      ]
    });

    const rawContent = response.choices[0]?.message?.content ?? '';
    const result: VerificationResult = JSON.parse(rawContent);

    return json(result);
  } catch (err) {
    console.error('Verification error:', err);
    return json({ message: 'Verification failed. Please try again.' }, { status: 500 });
  }
};