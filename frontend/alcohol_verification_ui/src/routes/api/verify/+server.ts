// MIT License
// Copyright (c) 2026 Mark Biegel
// See LICENSE file for full license text.

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request }) => {
	try {
		const formData = await request.formData();

		// Forward directly to your Python backend
		const response = await fetch('http://localhost:8000/verify', {
			method: 'POST',
			body: formData // pass formData straight through
		});

		if (!response.ok) {
			throw new Error(`Python backend error: ${response.status}`);
		}

		const result = await response.json();
		return json(result);
	} catch (err) {
		console.error('Verification error:', err);
		return json({ message: 'Verification failed. Please try again.' }, { status: 500 });
	}
};
