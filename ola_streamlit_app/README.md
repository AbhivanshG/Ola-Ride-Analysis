# Ola Ride Analytics (Streamlit app)

A 6-page dashboard built from `cleaned_eda_data.csv`:
Overall, Vehicle Type, Revenue, Cancellation, Ratings, Data & Cleaning.

## Folder contents
- `app.py`             - the whole app (heavily commented)
- `requirements.txt`   - libraries Streamlit Cloud installs for you
- `data/`              - the CSV file
- `assets/`            - Ola logo and vehicle pictures taken from your slides
- `.streamlit/config.toml` - colours (green theme)

## Run it on your own computer (optional test)
1. Install Python from python.org (tick "Add Python to PATH").
2. Open Command Prompt inside this folder and run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Your browser opens the app.

## Deploy it free on Streamlit Community Cloud (no coding needed)
1. Create a free account at https://github.com
2. Click **New repository**, name it `ola-dashboard`, set it to **Public**, click **Create**.
3. Click **uploading an existing file**, then drag in EVERYTHING inside this folder
   (`app.py`, `requirements.txt`, the `data` folder, the `assets` folder and the `.streamlit` folder).
   Click **Commit changes**.
   Tip: if the `.streamlit` folder is hidden, turn on "Hidden items" in File Explorer.
   The app still works without it, only the colours change.
4. Go to https://share.streamlit.io and sign in with GitHub.
5. Click **Create app**, choose your `ola-dashboard` repository, branch `main`,
   main file path `app.py`, then click **Deploy**.
6. After 2-3 minutes you get a public link to put in your project report.

## Common problems
- **ModuleNotFoundError**: make sure `requirements.txt` was uploaded.
- **Data file not found**: the CSV must be at `data/cleaned_eda_data.csv`. The app also lets you upload it by hand.
- **App is "sleeping"** after some days: open the link and click "Yes, get this app back up".
