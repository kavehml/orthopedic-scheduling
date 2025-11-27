# Quick Deployment Guide - Railway (Easiest & Free)

## Step 1: Push to GitHub

### A. Create GitHub Account
- Go to https://github.com/signup
- Sign up (it's free)

### B. Create Repository
1. Go to https://github.com/new
2. **Repository name**: Type `orthopedic-scheduling` (or any name you want)
3. **Description**: (optional) "Resident Scheduling System"
4. **Visibility**: Choose **Private** (recommended) or Public
5. **IMPORTANT**: 
   - ❌ **Don't** check "Add a README file"
   - ❌ **Don't** check "Add .gitignore" 
   - ❌ **Don't** choose a license
6. Click **"Create repository"**
7. **Copy the URL** shown on the next page (looks like: `https://github.com/YOUR_USERNAME/orthopedic-scheduling.git`)

### C. Push Your Code
**Open Terminal on your Mac** (Press Cmd+Space, type "Terminal", press Enter)

**Then copy and paste these commands one by one** (replace YOUR_USERNAME with your GitHub username):

```bash
# 1. Go to your project folder
cd "/Users/kaveh/Documents/Work and Study/McGill/Dr. Aoude/Scheduling"

# 2. Initialize git
git init

# 3. Add all files
git add .

# 4. Create first commit
git commit -m "Initial commit"

# 5. Connect to your GitHub repository
# REPLACE YOUR_USERNAME with your actual GitHub username
# REPLACE orthopedic-scheduling if you used a different repository name
git remote add origin https://github.com/YOUR_USERNAME/orthopedic-scheduling.git

# 6. Push to GitHub
git branch -M main
git push -u origin main
```

**Important Notes**:
- When you run `git push`, you'll be asked for:
  - **Username**: Your GitHub username
  - **Password**: You need a **Personal Access Token** (not your regular password)
  
- **To create a Personal Access Token**:
  1. Go to GitHub.com → Click your profile (top right) → **Settings**
  2. Scroll down → **Developer settings** (left sidebar)
  3. Click **Personal access tokens** → **Tokens (classic)**
  4. Click **Generate new token** → **Generate new token (classic)**
  5. **Note**: "Deployment Token"
  6. **Expiration**: 90 days (or No expiration)
  7. **Select scopes**: Check **"repo"** (this selects all repo permissions)
  8. Click **Generate token**
  9. **COPY THE TOKEN** (you won't see it again!)
  10. Use this token as your password when `git push` asks for it

---

## Step 2: Deploy on Railway

1. **Go to Railway**: https://railway.app

2. **Sign up with GitHub**:
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your GitHub
   - Select your `orthopedic-scheduling` repository

3. **Railway will auto-detect**:
   - It will detect Python automatically
   - It will install dependencies from `requirements.txt`
   - It will run the app

4. **Add Environment Variable** (if needed):
   - Go to your project → Variables
   - Add: `PORT` = `5000` (Railway usually sets this automatically)

5. **Get your URL**:
   - Railway will give you a URL like: `https://orthopedic-scheduling-production.up.railway.app`
   - Click on it to open your app!

---

## That's it! 🎉

Your app is now live online. Share the Railway URL with your team.

### Cost
- **Free**: $5 credit/month (usually enough for a scheduling app)
- After free credit: Pay-as-you-go (very cheap, ~$5-10/month)

### Features Available
✅ All features work exactly as they do locally
✅ Schedule optimization
✅ Resident management
✅ Year view & Student view
✅ PDF downloads
✅ Configuration management

---

## Alternative: Google Cloud Run (Also Free, More Generous)

If you prefer Google Cloud Run (more free tier, but slightly more setup):

1. **Install Google Cloud SDK**: https://cloud.google.com/sdk/docs/install
2. **Run these commands**:
```bash
gcloud auth login
gcloud projects create orthopedic-scheduling
gcloud config set project orthopedic-scheduling
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
gcloud run deploy orthopedic-scheduling --source . --platform managed --region us-central1 --allow-unauthenticated
```

**Free tier**: 2 million requests/month (usually completely free)

---

## Need Help?

If you run into issues:
1. Check the Railway logs (in Railway dashboard)
2. Make sure all files are pushed to GitHub
3. Verify `requirements.txt` has all dependencies

