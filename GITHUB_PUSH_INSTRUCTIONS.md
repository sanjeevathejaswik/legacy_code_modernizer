# How to Push Code to GitHub

## Prerequisites

- Git installed on your machine
- A GitHub account
- A GitHub repository already created at github.com/new

---

## One-Time Setup (First Push)

### 1. Initialize Git (if not already done)
```bash
git init
```

### 2. Add the Remote Repository
```bash
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
```

### 3. Stage All Files
```bash
git add .
```

### 4. Create Your First Commit
```bash
git commit -m "Initial commit"
```

### 5. Push to GitHub
```bash
git push -u origin master
```

> The `-u` flag sets the upstream so future pushes only need `git push`.

---

## Subsequent Pushes (After First Push)

```bash
git add .
git commit -m "Your commit message"
git push
```

---

## Pushing a Specific Branch

```bash
git checkout -b feature/my-feature
git add .
git commit -m "Add new feature"
git push -u origin feature/my-feature
```

---

## Authentication

GitHub no longer supports password authentication for git operations. Use one of the following:

### Option A — HTTPS with Personal Access Token (PAT)
1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Select the **repo** scope
4. Copy the token and use it as your password when prompted during `git push`

### Option B — SSH Key
1. Generate a key:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
2. Copy the public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
3. Add it to **GitHub → Settings → SSH and GPG keys → New SSH key**
4. Change your remote to SSH:
   ```bash
   git remote set-url origin git@github.com:<your-username>/<your-repo-name>.git
   ```

---

## Common Commands Reference

| Command | Description |
|---|---|
| `git status` | Show changed files |
| `git log --oneline` | Show commit history |
| `git remote -v` | Show remote URLs |
| `git pull` | Fetch and merge latest changes |
| `git push` | Push commits to remote |

---

## This Project

- **Repository:** https://github.com/sanjeevathejaswik/legacy_code_modernizer
- **Branch:** master
- **Remote:** origin
