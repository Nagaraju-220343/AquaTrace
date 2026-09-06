# AquaTrace: Marine Anomaly Detection

## The Problem
Underwater inspections using side-scan sonar and synthetic aperture sonar produce massive amounts of imagery. Analyzing this imagery manually for anomalies—such as shipwrecks, discarded fishing gear, lost cargo, or environmental hazards—is a tedious, time-consuming, and error-prone process. The sheer volume of data often causes fatigue in human operators, leading to missed detections or false positives.

## Our Solution
AquaTrace automates the detection of marine anomalies using a multi-stage machine learning pipeline. By processing sonar imagery through state-of-the-art computer vision models, our system can quickly and accurately identify objects on the seafloor.

Our pipeline features:
1. **Preprocessing & Artifact Removal**: Detects motion blur, dropouts, and applies Lee adaptive speckle filtering to enhance image quality.
2. **YOLO-based Object Detection**: Rapidly identifies potential anomalies.
3. **False Positive Filtering & Validation**: Analyzes detections for acoustic shadows and spatial properties to reduce false alarms.
4. **Confidence Calibration**: Adjusts detection confidence based on environmental noise and motion quality.
5. **Geotagging**: Translates pixel bounding boxes into real-world latitude and longitude coordinates.

## Project Structure
- `/backend`: FastAPI Python server containing the ML pipeline, endpoints, and database logic.
- `/frontend`: React.js web dashboard built with Vite for visualizing results, analytics, and geographical mapping.

## Getting Started

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```
   The backend will be available at `http://127.0.0.1:8000`.

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`.
