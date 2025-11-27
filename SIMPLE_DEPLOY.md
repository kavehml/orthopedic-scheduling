# Simple Deployment Guide - Step by Step

## Part 1: Create GitHub Repository

1. **Go to GitHub.com** and sign in (or create account if needed)

2. **Click the "+" icon** (top right) → **"New repository"**

3. **Fill in the form**:
   - **Repository name**: `orthopedic-scheduling` (or any name you like, e.g., `resident-scheduler`)
   - **Description**: (optional) "Orthopedic Surgery Resident Scheduling System"
   - **Visibility**: Choose **Private** (recommended) or Public
   - **DO NOT** check "Add a README file" (we already have one)
   - **DO NOT** check "Add .gitignore" (we already have one)
   - **DO NOT** choose a license

4. **Click "Create repository"**

5. **Copy the repository URL** - GitHub will show you a page with commands. Look for a URL like:
   ```
   https://github.com/YOUR_USERNAME/orthopedic-scheduling.git
   ```
   Copy this URL - you'll need it in the next step.

---

## Part 2: Push Your Code to GitHub

**Where to run commands**: Open **Terminal** on your Mac (search "Terminal" in Spotlight)

**Run these commands one by one** (copy and paste each line, press Enter):

```bash
# 1. Go to your project folder
cd "/Users/kaveh/Documents/Work and Study/McGill/Dr. Aoude/Scheduling"

# 2. Initialize git (if not already done)
git init

# 3. Add all your files
git add .

# 4. Create first commit
git commit -m "Initial commit"

# 5. Add your GitHub repository
# REPLACE YOUR_USERNAME with your actual GitHub username
# REPLACE orthopedic-scheduling with your repository name if different
git remote add origin https://github.com/YOUR_USERNAME/orthopedic-scheduling.git

# 6. Push to GitHub
git branch -M main
git push -u origin main
```

**Important**: 
- When you run `git push`, GitHub will ask for your username and password
- For password, you'll need a **Personal Access Token** (not your regular password)
- To create one: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- Give it "repo" permissions
- Copy the token and use it as your password

---

## Part 3: Deploy on Railway

1. **Go to**: https://railway.app

2. **Click "Start a New Project"**

3. **Click "Deploy from GitHub repo"**

4. **Authorize Railway** to access your GitHub (click "Authorize Railway")

5. **Select your repository** (`orthopedic-scheduling`)

6. **Wait 2-3 minutes** - Railway will automatically:
   - Detect it's a Python app
   - Install dependencies
   - Deploy your app

7. **Get your URL**:
   - Railway will show you a URL like: `https://orthopedic-scheduling-production.up.railway.app`
   - Click on it or copy it
   - **That's your live app!** 🎉

---

## Troubleshooting

**If git push asks for password**:
- Use a Personal Access Token (see instructions above)
- Or use GitHub Desktop app (easier for beginners)

**If Railway deployment fails**:
- Check the logs in Railway dashboard
- Make sure `requirements.txt` exists and has all dependencies

**Need help?** Let me know which step you're stuck on!

