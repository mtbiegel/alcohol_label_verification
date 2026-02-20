# ProofCheck™ - Take Home Assessment Reflection

**Author:** Mark Biegel  
**Project:** TTB Label Verification System
**Description:** AI-Powered Alcohol Label Verification Tool  
**Date:** February 20th, 2026 (Developed in a single week)

## Summary

This document outlines the design decisions, technical approaches & challenges encountered, and potential improvements for the ProofCheck™ - TTB Label Verification system. The application was built as a proof-of-concept to demonstrate AI-powered compliance checking for alcohol beverage labels against TTB requirements.

For more/other info, read `README.md` and `MY_THOUGHTS.md`

## Assumptions Made

1. **Access to Azure with openAI API endpoints available**
   - openAI API endpoints have been available as of early 2026 at FedRAMP High, meaning the openAI API calls will work
2. **User Expertise:** Users understand TTB label requirements and can upload correctly formatted files
3. **Image Quality:** Labels are resonably clear, well-lit, and OCR-readable (no EXTREME angles or blurriness)
4. **Government Warning:** Standard TTB warning text is constant and known
5. **File Naming:** Users follow the `name_image` + `name_application` convention
6. **Network:** Stable internet connection for API calls
7. **Computer/Browser:** Modern computer hardware and browser (Chrome, Firefox, Safari, Edge)

## Technology Stack/Tools

<table>
  <tr>
  <td>

**Frontend:**

- **NodeJS**
- **Svelte 5 & SvelteKit**
- **TypeScript**
- **Tailwind CSS**
- **Prettier** - Formatting
</td>
<td>

**Backend:**

- **FastAPI**
- **Python 3.12**
- **RapidFuzz**
- **OpenAI GPT-4o-mini Vision API** (Vision LLM for field extraction from label images)
- **Ruff** - Formatting
- **Railway** - Host webapp
</td>
  </tr>
</table>

## Core Features Implemented

<table>
  <tr>
  <td>

**1. Intelligent Text Field Extraction**

**AI Integration** - Vision LLM (GPT-4o-mini) extracts fields directly from images

</td>
<td>

**2. Manual Review Workflow**

**Override capabilities & Audit trail:** All overrides marked in CSV export

**Three-tier status system:** Approved, Needs Review, Critical failures

</td>
<td>

**3. Batch Processing**

**Sequential processing**
**Progress tracking**
**Error isolation** - One failed pair doesn't break the entire batch

</td>
<td>

**4. CSV-based application data** - Easy for batch processing
**Drag-and-drop interface** - User-friendly file upload
**File validation:** Strict type checking (.jpg, .png, .webp, .csv only)

</td>
  </tr>
</table>

## Technical Decisions Made

<table>
  <tr>
  <td>

**1. Vision LLM vs. Local OCR**

**Initial Consideration:** PaddleOCR + heuristic classification

**Final Decision:** OpenAI Vision API

**Rationale:**

- **Accuracy:** 95%+ field extraction vs. ~65% with local OCR
- **Simplicity:** Single API call vs. complex text parsing logic
- **Maintainability:** LLM adapts to label variations naturally
- **Speed:** 2-4 seconds per image (within 5-second requirement)

**Trade-off:** Dependency on external API and associated costs (~$0.01 per label)

</td>
<td>

**2. Comparison Logic**

**Fuzzy Matching for Text Fields:**

- **Brand Name:** 85% similarity threshold with length validation
- **Class/Type:** Substring matching + 80% fuzzy match
- **Rationale:** Handles OCR artifacts and case differences

**Exact Matching for Regulatory Fields:**

- **Alcohol Content:** Number must match exactly (format flexible)
- **Net Contents:** Number and unit must both match
- **Government Warning:** 95%+ similarity (stricter due to legal requirements)
</td>
<td>

**3. Batch Sizing and File Configuration**

**Default:** 4 pairs per API call

**Reasoning:**

- Balances speed vs. error recovery
- Provides frequent progress updates
- Prevents timeout on slower connections
- Manageable memory footprint

**NOTE:**

- Used `.csv` files for application data upload over `.json` because after working on government projects at my job, I am aware that in existing legacy government systems, it is the norm for .csv files to be used over `.json` files as excel is very much an integral part of systems.

</td>
  </tr>
</table>

## Challenges & Solutions

### Challenge 1: Bad local CPU-based classifier accuracy

**Problem:** The CPU-based machine learning OCR and classification approach produced inconsistent results and often failed on edge cases, making it unsuitable for accurate label verification.

**Solution:** Attempted GPU-based machine learning OCR, but ended up switching to OpenAI’s Vision API for field extraction to ensure high accuracy and reliability in processing each label.

**Better Approach:** Future improvements could include training a custom GPU-based model or using optimized local OCR pipelines to reduce dependency on external APIs.

### Challenge 2: No local GPU accessible for custom ML model development (& not enough time for this)

**Problem:** GPU-based models would allow higher performance and more flexibility, but hardware limitations prevented testing or deployment of GPU solutions.

**Solution:** Switched to using OpenAI’s Vision API for field extraction to ensure high accuracy and reliability in processing
each label.

**Better Approach:** With access to a GPU, implement a hybrid system consisting of a fully localized system that leverages trained models on alcohol labels for faster processing while keeping API calls as a fallback for difficult cases.

### Challenge 3: RateLimitError from openAI API

**Problem:** High-volume API requests occasionally hit rate limits, slowing down batch verification and causing RateLimitError messages from openAI API when doing larger batches (20+ images). Attempted to shrink down the prompt as much as possible without losing too much detail with what needed to be done. In the future, try shrinking the image sizes for less tokens per image.

**Solution:** Implemented batch processing with throttling and error handling to retry requests and ensure all pairs were processed.

**Better Approach:** Consider caching frequent responses, spreading requests over time, or requesting higher-rate API quotas to improve throughput.

## What I Would Improve Going Forward With More Time

<table>
  <tr>
  <td>

**1. Automated Testing, and more testing in general**

Unit tests for comparison logic

Integration tests for API endpoints

Not tested enough due to time constraint:

- Load testing (100+ concurrent users)
- Performance with very large images (10MB+)
- SQL injection or XSS attacks (not applicable to current architecture)
  </td>
  <td>

**2. AI/LLM & Image Preprocessing**

Self-contained model that’s trained on alcohol image labels and running locally (no external providers needed).

Decrease image size

Detect and crop multiple labels in one image

</td>
<td>

**3. Backend Improvements**

Audit Trail: Log all verifications with timestamps

Performance Optimization

</td>
<td>

**4. UI Enhancements**

Dark mode

Keyboard shortcuts (j/k for navigation)

Customizable batch size in UI

A way to view past label verifications in the UI

Animations on the front end

Maybe optimized for mobile (if this ever is run on a mobile device)?

</td>
  </tr>
</table>
