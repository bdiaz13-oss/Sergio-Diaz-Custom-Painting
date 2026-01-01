```markdown
# Diaz Custom Painting — Referral-friendly Flask app

What this project is
- A small Flask app to manage referral codes and capture estimate requests for a local painting business.
- Public request form that accepts referral codes (or referrer names).
- Admin area (password via env var) to create referrers, view leads, credit referrers, and export leads CSV.
- API endpoint to receive leads from Google Forms via Apps Script and to validate referral codes.

Quick start (local)
1. Install Python 3.10+.
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate    # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set environment variables (example):
   ```
   export FLASK_APP=app.py
   export FLASK_DEBUG=1
   export SECRET_KEY="pick-a-random-secret"
   export ADMIN_PASSWORD="choose-a-strong-password"
   ```
   Optionally set DATABASE_URL (default: sqlite:///data.db).
4. Run locally:
   ```
   flask run
   ```
   or
   ```
   python app.py
   ```
5. Visit http://localhost:5000/ — admin area is at /admin (login with ADMIN_PASSWORD).

Google Sites + Google Forms integration
- Option A — Embed the Flask /request-estimate page:
  - Make your Flask site publicly accessible (ngrok for testing, Render, Railway, or a VPS) and embed the page in Google Sites (iframe/embed).
  - Note: embedding may be blocked by some CSP or hosting providers; test carefully.

- Option B — Use Google Form + Apps Script (recommended if you prefer Google Sites + Form UI):
  1. Create a Google Form with fields:
     - Name, Phone, Email, Referral code, Referrer name, Project type, Rooms or area, Budget range, Preferred timeline, Notes
  2. In the Form editor open Extensions -> Apps Script and add this snippet (replace FLASK_URL):
     ```javascript
     function onFormSubmit(e){
       var responses = e.namedValues;
       var payload = {
         name: responses["Name"] ? responses["Name"][0] : "",
         phone: responses["Phone"] ? responses["Phone"][0] : "",
         email: responses["Email"] ? responses["Email"][0] : "",
         referrer_code: responses["Referral code"] ? responses["Referral code"][0] : "",
         referrer_name: responses["Referrer name"] ? responses["Referrer name"][0] : "",
         project_type: responses["Project type"] ? responses["Project type"][0] : "",
         rooms: responses["Rooms or area"] ? responses["Rooms or area"][0] : "",
         budget_range: responses["Budget range"] ? responses["Budget range"][0] : "",
         timeline: responses["Preferred timeline"] ? responses["Preferred timeline"][0] : "",
         notes: responses["Notes"] ? responses["Notes"][0] : ""
       };
       var options = {
         'method' : 'post',
         'contentType': 'application/json',
         'payload' : JSON.stringify(payload)
       };
       var FLASK_URL = "https://your-flask-site.example.com/api/leads";
       UrlFetchApp.fetch(FLASK_URL, options);
     }
     ```
  3. Install an onFormSubmit trigger in Apps Script to call onFormSubmit for each response.

Recommended workflow for a small two-person business
- Use Google Sites as the marketing front (Home, Gallery, Testimonials).
- Use the Google Form embedded in the Request Estimate page and forward submissions to the Flask app via Apps Script.
- After each completed job, create a Referrer entry in the admin (one-time) and give the past customer the code by SMS or tell them the short code verbally. They can pass that code to friends — when a friend uses it, the lead is flagged as a referral.

Security & production notes
- Replace ADMIN_PASSWORD with a strong password and SECRET_KEY with a secure random string before making the app public.
- Add proper authentication for /admin (this project uses a simple password/session for convenience; replace with real auth for production).
- Serve over HTTPS in production.
- Use a reliable database for production (Postgres) instead of SQLite if you expect concurrent writes or heavier usage.
- Consider adding email (SendGrid/Mailgun) or SMS notifications for new referred leads.

Next steps I can help with
- Package this into a GitHub repo and open a PR (I can guide you through pushing these files).
- Add email notifications (SendGrid) so the owner receives an email when a referred lead arrives.
- Deploy a small instance (Render / Railway / Heroku) and configure env vars.
- Add photo uploads (S3) for gallery and lead attachments.

TODO / notes
- The admin auth is intentionally simple — replace before exposing publicly.
- This repo contains placeholder images; add real photos under static/images/ before publishing.
```
