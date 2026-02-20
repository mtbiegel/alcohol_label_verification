# ProofCheck™ - A TTB Alcohol Label Verification App

ProofCheck™ is an AI-powered tool for automatically verifying alcohol beverage labels against TTB (Alcohol and Tobacco Tax and Trade Bureau) compliance requirements. Given an image of a product label and structured application information (e.g., brand name, alcohol percentage, producer details), the system analyzes the label and easily displays the results and a valid/invalid dertermination, indicating whether each field matches.

PUBLIC URL: `https://alcohollabelverification-production.up.railway.app/`

READ `MY_THOUGHTS.md`: This file goes over my thoughts, decisions, and approaches during this project in an informal, colloquial format.

READ `PROJECT_REFLECTION.md`: This files is a formal review and techical reflection of the decision and approach I took.

## Features

- Single and batch label verification
- AI-powered and fallback algorithmic field text-extraction (brand name, class/type, alcohol content, net contents, government warning)
- Manual override and review capabilities of each image
- CSV export of verification results
- Image preview alongside results

## Prerequisites

Before you begin, ensure you have the following installed:
_NOTE: Other versions may work but have not been tested on, so no guarentee that other versions will work_

- **Python 3.12** ([Download](https://www.python.org/downloads/))
- **Node.js v20.20.0** ([Download](https://nodejs.org/)) - FYSA: npm v10.8.2 and nvm v0.39.7 have been tested.
- **Git** ([Download](https://git-scm.com/downloads))
- **openAI API Key** - Either trial version or paid version is needed ($5 will be enough to test 1000+ verification runs)
- **macOS or Linux Distros** - _Only Ubuntu 24.04 has been tested_

## Development Installation and Runtime (not for deployment)

### 1. Clone the Repository

```bash
git clone git@github.com:mtbiegel/alcohol_label_verification.git
```

or if HTTPS cloning is requierd:

```bash
https://github.com/mtbiegel/alcohol_label_verification.git
```

Then,

```bash
cd alcohol_label_verification
```

### 2. Backend Setup

**In top-level folder, create a virtual environment and activate:**

```bash
python3.12 -m venv <NAME_OF_VIRTUAL_ENV>
source venv/bin/activate
```

**Install Python dependencies:**
Navigate to the backend directory:

```bash
cd backend/src
pip install -r requirements.txt
```

**Configure environment variables:**

Create a `.env` file in the `backend` directory:

```bash
OPENAI_API_KEY=<YOUR_API_KEY_HERE>
```

_NOTE: If the API key is not found during runtime, fall back to exporting API key to PATH. This will have to be done in every terminal that wants to run FastAPI (or add to `~/.bashrc`):_

```bash
export OPENAI_API_KEY=<YOUR_API_KEY_HERE>
```

Now, time to set up the front end!

### 3. Frontend Setup

Open a new terminal at the top level of this project, and navigate to the frontend directory:

```bash
cd frontend/alcohol_verification_ui
```

**Install Node.js dependencies:**

```bash
npm install
```

## Running the Application

You'll need **two terminal windows** - one for the backend and one for the frontend.

### Terminal 1: Start the Backend

From the top level project directory and with virtual environment activated, navigate to the backend directory and set up the Python environment:

```bash
cd backend/src
```

Run the following command to launch the FastAPI server with uvicorn

```bash
uvicorn api:app --port 8000 --reload
```

You should get a confirmation that the application has started:

```bash
INFO:     Will watch for changes in these directories: ['/alcohol_label_verification/backend/src']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [3551953] using StatReload
INFO:     Started server process [3551955]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The backend API will be available at `http://localhost:8000`

_NOTE: If an error returns saying the API key is not found, fall back to exporting API key to PATH:_

```bash
export OPENAI_API_KEY=<YOUR_API_KEY_HERE>
```

### Terminal 2: Start the Frontend

```bash
cd frontend/alcohol_verification_ui
npm run dev
```

The frontend will be available at `http://localhost:5173`

## How To Use

#### Prerequisites:

For this application, you will need to have an image and application at the ready.

**The BEST way to learn how to use ProofCheck™ - Click "Using ProofCheck™ button on home page:**

After starting both the frontend and backend (in separate terminals):

1. Open your browser and navigate to `http://localhost:5173`
2. Click the "Using ProofCheck™" button in the top right to view and learn how to use this applicaiton. This is the best way to learn the application.

If you prefer verbosity in this readme file, the instructions are outlined here:

### How to use ProofCheck™

#### 1. Proper Application Format - Download the Template:

Download the application template from the button in the top right corner named `Download Template`. Use this template as the starting point for bottlers and producers to input data; this way, data can easily be loaded into the ProofCheck™ with the correct fields. Valid fields are as follows:

- Brand Name
- Class/Type
- Alcohol content Amount
- Alocohol Content Format
- Net Content Amount
- Net Content Format
- Producer Name

An example image is: ![here](examples/readme_example_label.png)

And the proper fields for the CSV are as follows:

- Brand Name: "Midnight Ember"
- Class/Type: Bourbon Whiskey
- Alcohol content Amount: 47
- Alocohol Content Format: %
- Net Content Amount: 750
- Net Content Format: mL
- Producer Name: Midnight Ember Distillery

Once the information is populated into the CSV fields, follow the next step for file naming scheme. Click the "Example Data (ZIP)" button in the web app or navigate to `/frontend/alcohol_verification_ui/static/example_pairings.zip` (in the repo) to get example data and for testing.

#### 2. Proper File Naming Scheme

Rename files such that the image file has `<_LABEL_NAME>_image.ext`, replacing `<LABEL_NAME>` with a constant name, adding the `_image.ext` where `.ext` is the original image extension (i.e `.jpg`, `.png`, `.webp`). Repeat this process for the application file: `<_LABEL_NAME>_application.csv`, replacing `<LABEL_NAME>` with the same constant name used on the image, adding the `_application.csv` suffix. As a result, the image and application file pair have the same constant name you defined as the prefix with corresponding suffixes.

Example of a pair with proper naming:

- `corona_extra_image.png`
- `corona_extra_application.png`

Example of another pair with proper naming:

- `smirnoff_ice_original_image.webp`
- `smirnoff_ice_original_aplication.csv`

#### 3. Upload Image & Application Pair

There are 2 methods to upload image and application pairs: You can drag and drop the image and application pair into the drop zone, or you can click the upload box and browse for image and applicaiton pair through the OS. A pair is needed to run a verification. Once you select a pair, it will show up in the "Uploaded Pairs" section and tell you if the pair is ready for valdiating or if it is missing an entry (i.e missing the image or the application).

#### 4. Run Validation

Once you have valid pair(s), click the "Verify" button at the bottom of the webpage. The processing will start and route you to the Results page once completed. Each pair validation takes approximately 5 seconds to complete. The UI will let you know of any invalid pairs. Clicking the "Verify" button will prompt you with a warning that a pair(s) is incomplete. Incomplete pairs will not be processed.

#### 5. Results & Downloadables

Once pair(s) have been processed and redirected to the Results page, there will be the following attributes: Count for total, approved, needs-review, and rejected categories. Below that is the individual hueristcs of the processed pairs with more detail about the results; next to that is an image preview of the label you are observing. You are able to toggle through all the pair results if you uploaded multiple pairs.

You are able to download the hueristics from this validation run with the "Download All Results as CSV" button.

If you uploaded multiple pairs to perform a batch verification, you will see a progress bar at the top of this page showing how many pairs are still processing.

## Testing

### How to test:

1. Open the deployed web application in your browser.
2. Upload an/multiple label image and application pair(s) using the file upload interface.
3. Submit the form for verification.
4. Review the returned results on the dashboard.
   - Each field should indicate whether it matches the label.
5. Repeat with different label pairs and batch test sets to confirm consistent validation behavior.

Expected behavior:
The system analyzes the label image and returns clear match/non-match indicators for each application field without errors or crashes.

### Where to test:

**Web-based Testing:**

This is the best approach to take when testing new functionality (through an instance either localhost or public URL) of the application. Test files can be uploaded to the site directly, and print/consolge.log statements can be used and viewed in respective terminals for troubleshooting.

**Local Testing (deprecated):**

The `/tests` folder is for individual unit testing of the backend code separately. This is typically used when running the Python files individually (running through Python main function). However, once front-end development was completed, the best way to test functionality is through an instance (either localhost or public URL) of the application.

## File Format

**Application CSV Template:**

Download the template from the application or create a CSV with these headers:

```csv
brand_name,class_type,alcohol_content_amount,alcohol_content_format,net_contents_amount,net_contents_unit,producer_name
Midnight Ember,Smoky Bourbon Whiskey,47,%,750,mL,Midnight Ember Distillery
```

## Troubleshooting

**Before troubleshooting any errors, make sure all the requied packages are installed, the virtual enviroment is sourced (Python 3.12), and you have the latest version of the code.**

**Backend won't start:**

- Ensure your virtual environment is activated
- Verify all dependencies installed: `pip list`
- Check that port 8000 is not in use

**Frontend won't start:**

- Clear node modules and reinstall: `rm -rf node_modules && npm install`
- Check that port 5173 is not in use

**404 errors when verifying:**

- Ensure both backend and frontend are running
- Verify backend is on port 8000 and frontend on port 5173

## Configuration

**Batch Processing Size:**
From the front-end, the batch size is constant at 4 image-app pairs by default. This is enough to process multiple images while avoiding any API RateLimit errors, although RateLimit errors may still occur with 15+ requests within a minute. The backend code is able to handle RateLimit errors and will delay the processing of any more images until the RateLimit Error subsides.

The developer is able to adjust the batch size here:
`frontend/src/routes/+page.svelte`:

```typescript
const BATCH_SIZE = 4; // Process 4 pairs at a time
```

**Model Selection:**

The system uses OpenAI's Vision API via GPT-4o-mini by default. To change models, edit `backend/label_classifier.py`.

**Other notes**
This entire project was developed SUPER quickly in a single week from the dates 2/13/2026 to 2/20/2026. Keep in mind during webapp use.

## License

License information can be found in the `LICENSE` file at the top level directory of the project. The file will state:

Copyright (c) 2026 Mark Biegel

All rights reserved.

This software and its source code may not be used, copied, modified, or distributed in any form, including internal or commercial use, without the explicit written permission of the copyright holder.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
