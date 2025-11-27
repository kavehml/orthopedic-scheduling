# Deployment Guide

This guide will help you deploy the Orthopedic Surgery Resident Scheduling System online.

## Option 1: Google Cloud Run (Recommended - Free Tier Available)

### Prerequisites
1. Google Cloud account (free tier available)
2. Google Cloud SDK installed (`gcloud` command)
3. Project created on Google Cloud

### Steps

1. **Install Google Cloud SDK** (if not already installed):
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Login to Google Cloud**:
   ```bash
   gcloud auth login
   ```

3. **Create a new project** (or use existing):
   ```bash
   gcloud projects create orthopedic-scheduling --name="Orthopedic Scheduling"
   gcloud config set project orthopedic-scheduling
   ```

4. **Enable required APIs**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   ```

5. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy orthopedic-scheduling \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 512Mi \
     --timeout 300
   ```

6. **Get your URL**:
   After deployment, you'll get a URL like: `https://orthopedic-scheduling-xxxxx.run.app`

### Cost
- **Free tier**: 2 million requests/month, 360,000 GB-seconds memory, 180,000 vCPU-seconds
- For a small scheduling app, this should be **completely free**

---

## Option 2: GitHub + Railway (Free Tier Available)

### Steps

1. **Create GitHub repository**:
   - Go to GitHub.com
   - Click "New repository"
   - Name it (e.g., "orthopedic-scheduling")
   - Don't initialize with README (you already have files)
   - Click "Create repository"

2. **Push your code to GitHub**:
   ```bash
   cd "/Users/kaveh/Documents/Work and Study/McGill/Dr. Aoude/Scheduling"
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/orthopedic-scheduling.git
   git push -u origin main
   ```

3. **Deploy on Railway**:
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and deploy
   - Add environment variable: `PORT=5000`

### Cost
- **Free tier**: $5 credit/month (usually enough for small apps)
- After free tier: Pay-as-you-go

---

## Option 3: GitHub + Render (Free Tier Available)

### Steps

1. **Push to GitHub** (same as Option 2, steps 1-2)

2. **Deploy on Render**:
   - Go to https://render.com
   - Sign up with GitHub
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
     - **Environment**: Python 3
   - Click "Create Web Service"

### Cost
- **Free tier**: Available but with limitations (spins down after inactivity)
- **Paid**: $7/month for always-on

---

## Important Notes

1. **Data Persistence**: 
   - `data.json` and `config.json` are stored in the container
   - For production, consider using a database (PostgreSQL) or cloud storage
   - Current setup works but data is lost if container restarts

2. **Environment Variables**:
   - `PORT`: Set automatically by hosting platform
   - `FLASK_DEBUG`: Set to `False` for production

3. **Security**:
   - The app currently has no authentication
   - Consider adding login/password protection for production use

4. **Backup**:
   - Regularly backup `data.json` and `config.json`
   - These contain all your schedule data

---

## Quick Start (Google Cloud Run)

If you want the fastest deployment:

```bash
# 1. Install gcloud (if needed)
# 2. Login
gcloud auth login

# 3. Create project
gcloud projects create orthopedic-scheduling
gcloud config set project orthopedic-scheduling

# 4. Enable billing (required but free tier applies)
# Go to: https://console.cloud.google.com/billing

# 5. Deploy
gcloud run deploy orthopedic-scheduling --source . --platform managed --region us-central1 --allow-unauthenticated

# 6. Done! You'll get a URL
```

---

## Troubleshooting

- **Port errors**: Make sure `PORT` environment variable is set
- **Import errors**: Check `requirements.txt` has all dependencies
- **Data not saving**: Ensure file permissions allow writing

