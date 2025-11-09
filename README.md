# AKINDE_23CG034030_EMOTION_DETECTION_WEB_APP_V2

**Author**: Akinde (Matric: 23CG034030)

This is v2 of the Emotion Detection Web App with improvements based on feedback:
- Added server-side image annotation (labels the image with dominant emotion)
- Improved error handling and user-friendly messages
- Added `render.yaml` for Render.com deployment
- Added Download CSV feature for history

## Quick start (local)
1. Create & activate a virtualenv (recommended):
   - Windows:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   - Mac/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   If `tensorflow` fails, ensure you have `tensorflow-cpu==2.12.0` in requirements (already set).

3. Run the app:
   ```bash
   python app.py
   ```
   Visit http://localhost:5000

## Deploy to Render (free)
1. Push this repo to GitHub.
2. Create a new Web Service on Render, connect the repo.
3. You can either let Render auto-detect or use `render.yaml` (already included).
4. Ensure Python version is 3.10+.
5. If build fails due to memory, ensure `tensorflow-cpu` is used.
6. Set `FLASK_SECRET_KEY` to a random value in Render environment variables.
