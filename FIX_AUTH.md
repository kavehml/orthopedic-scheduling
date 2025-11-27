# Fix Authentication Error

## The Problem
GitHub no longer accepts passwords. You need a **Personal Access Token**.

## Solution: Create Personal Access Token

### Step 1: Create Token on GitHub

1. **Go to GitHub.com** and sign in
2. Click your **profile picture** (top right) → **Settings**
3. Scroll down in left sidebar → Click **"Developer settings"**
4. Click **"Personal access tokens"** → **"Tokens (classic)"**
5. Click **"Generate new token"** → **"Generate new token (classic)"**
6. Fill in:
   - **Note**: "Deployment Token" (or any name)
   - **Expiration**: Choose "90 days" or "No expiration"
   - **Select scopes**: Check **"repo"** (this gives full repository access)
7. Scroll down → Click **"Generate token"**
8. **IMPORTANT**: Copy the token immediately (it looks like: `ghp_xxxxxxxxxxxxxxxxxxxx`)
   - You won't see it again!
   - Save it somewhere safe

### Step 2: Use Token Instead of Password

When you run `git push`, it will ask:
- **Username**: `kavehml` (your GitHub username)
- **Password**: Paste your **Personal Access Token** (the `ghp_xxxxx` code you just copied)

### Step 3: Try Again

Run this command again:
```bash
git push -u origin main
```

When it asks for password, paste your token.

---

## Alternative: Use SSH (Easier Long-term)

If you want to avoid entering password/token every time, use SSH:

1. **Generate SSH key** (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
   (Press Enter 3 times to accept defaults)

2. **Copy your public key**:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Copy the entire output

3. **Add to GitHub**:
   - Go to GitHub.com → Settings → SSH and GPG keys
   - Click "New SSH key"
   - Paste your key
   - Click "Add SSH key"

4. **Change your remote URL to SSH**:
   ```bash
   git remote set-url origin git@github.com:kavehml/orthopedic-scheduling.git
   ```

5. **Try pushing again**:
   ```bash
   git push -u origin main
   ```

Now it won't ask for password!

