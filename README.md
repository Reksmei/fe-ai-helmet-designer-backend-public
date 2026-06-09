# Formula E AI Helmet Designer🏎️

![UI Example](https://storage.googleapis.com/fe-demo-branding/example_helmet_output_page)

The Formula E AI Helmet Designer is an interactive Generative Media application built on Google Cloud that allows users to design custom Formula E helmets from their imagination. Users choose a theme or motif, and a combination of state-of-the-art AI models brings their creation to life in high quality, complete with brand integrations and a 3D animated video.

## How it Works: Solution Architecture

<img src="https://storage.googleapis.com/fe-demo-branding/formula_e_helmet_demo_architecture.png" alt="Architecture Breakdown" align="right" width="450">

The full application is split into a React (Next.js) frontend and a Python (FastAPI) backend (which you're find out more about in this public repository), all deployed on a highly scalable Cloud Run instance. The backend acts as an orchestrator, securely connecting user inputs to a suite of Google Cloud Agent Platform models and managing asset storage via Cloud Storage.

1. **Gemini 3.5 Flash:** Takes the user's basic theme (e.g., "Ocean Waves") and uses its advanced reasoning capabilities to write a detailed, highly-optimized prompt.
2. **Nano Banana:** Generates high-fidelity, artistic motif designs using its advanced image generation capabilities across various artistic styles.
3. **Nano Banana 2:** Acts as the image editor and compositor, seamlessly wrapping the chosen motif and a the user's favorite racing team's logo onto a blank Formula E helmet template.
4. **Veo 3.1:** Animates the final 2D image into a seamless, rotating 3D product ad using enhanced camera controls and image-to-video capabilities.

*Once generated, all digital assets (images and videos) are uploaded to Cloud Storage and presented to the user via scannable QR codes for easy download as digital souvenirs.*

<br clear="all"/>

## Use Cases with Nano Banana 2

Nano Banana 2 is Google Cloud's state-of-the-art image generation and editing model, balancing photorealistisic quality with speed. Beyond this helmet design demo, Nano Banana 2 unlocks powerful enterprise use cases:

* **Marketing & Advertising Mockups:** Create vibrant posters, immersive ads, and high-fidelity product representations. Accurate text rendering allows for seamless localization and fast storyboard generation, reducing editing times from hours to seconds.

* **Professional Image Enhancement:** Transform low-quality user-uploaded photos into professional, studio-grade assets while preserving authentic textures and details.

* **UI/UX & Product Design Iteration:** Quickly iterate on icons, interface assets, and diagrams for product specs without losing responsiveness to direction, even after multiple rounds of editing.

* **Consistent Brand Storytelling:** Maintain subject consistency for characters and objects across multiple assets, building cohesive narratives and marketing collateral that adhere strictly to brand guidelines.

* **Dynamic Educational & Travel Visuals:** Power apps and educational tools with highly accurate, localized visuals driven by real-time world knowledge and search integration.

---

## How to Run the Backend Locally

### Prerequisites
* Python 3.10+
* Node.js & npm (for separate frontend)
* Google Cloud CLI (`gcloud`)


### Step 1: Clone the Repository & Configure Environment Variables
First, clone the repository to your local machine. Then, create a .env file in the root of your project directory.
You will need to add the environment variables found in main.py and replace the placeholder values in .env with your actual Google Cloud project details:
code
```
PROJECT_ID="your-google-cloud-project-id"
LOCATION="your-gcp-region" # use "global" as Nano Banana 2 only supports global at present
BUCKET_NAME="your-cloud-storage-bucket-name"
```
### Step 2: Authenticate with Google Cloud
To allow the application to interact with Agent Platform and Cloud Storage, you need to authenticate your local environment with your Google Cloud account. Run the following command in your terminal:
code
Bash
gcloud auth application-default login

### Step 3: Setup and Run the Backend
Next, you need to set up your Python environment, install the required dependencies, and start the backend server.

Create the virtual environment
```
python3 -m venv venv
```
Activate on macOS/Linux
```
source venv/bin/activate  
```
Activate on Windows
```
venv\Scripts\activate
```

Install the required Python packages:
```
pip install -r requirements.txt
```

Navigate to the backend folder and start the server:
```
cd Backend
python3 main.py
(The FastAPI backend will now be running at http://localhost:8000)
```
