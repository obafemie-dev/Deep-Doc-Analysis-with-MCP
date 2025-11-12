# Deployment Guide - Render

This guide walks you through deploying the Deep Doc Analysis app to **Render** using Claude API.

## Prerequisites

- ✅ Anthropic API key (Claude)
- ✅ GitHub account with repository
- ✅ Render account (free - sign up at https://render.com)

---

## 📦 **What Gets Deployed**

1. **Backend** (FastAPI + Claude API) - Web Service
2. **Frontend** (React) - Static Site

**Total Cost**:
- Free tier: $0/month (spins down after 15 min)
- Always-on: $7/month for backend only

---

## 🚀 **Deployment Steps**

### **Step 1: Prepare Your Repository**

```bash
# Make sure you're on the deploy branch
git checkout deploy/render-setup

# Push to GitHub
git push -u origin deploy/render-setup
```

### **Step 2: Deploy Backend (FastAPI)**

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository: `Deep-Doc-Analysis-with-MCP`
5. Select branch: `deploy/render-setup` (or your main branch)

**Configure the Backend:**

| Setting | Value |
|---------|-------|
| **Name** | `deep-doc-backend` (or your choice) |
| **Region** | Choose closest to you |
| **Branch** | `deploy/render-setup` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | **Free** (or Starter $7/mo for always-on) |

**Environment Variables** (click "Advanced"):

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `your_actual_api_key_here` |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` |
| `LLM_PROVIDER` | `claude` |
| `BACKEND_CORS_ORIGINS` | `["https://your-frontend-url.onrender.com"]` *(update after frontend deploy)* |
| `UPLOAD_DIR` | `/tmp/uploads` |
| `PYTHONUNBUFFERED` | `1` |

**Note**: Use `/tmp/uploads` for file storage (temporary, deleted on restart)

6. Click **"Create Web Service"**
7. Wait 5-10 minutes for deployment
8. Note your backend URL: `https://deep-doc-backend.onrender.com`

### **Step 3: Deploy Frontend (React)**

1. Back on Render dashboard
2. Click **"New +"** → **"Static Site"**
3. Select the same repository
4. Select branch: `deploy/render-setup`

**Configure the Frontend:**

| Setting | Value |
|---------|-------|
| **Name** | `deep-doc-frontend` |
| **Branch** | `deploy/render-setup` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | `dist` |

**Environment Variables**:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://deep-doc-backend.onrender.com/api/v1` *(use your actual backend URL)* |

5. Click **"Create Static Site"**
6. Wait 3-5 minutes for deployment
7. Your app is now live! 🎉

### **Step 4: Update CORS**

1. Go back to **Backend service** settings
2. Update the `BACKEND_CORS_ORIGINS` environment variable:
   ```
   ["https://deep-doc-frontend.onrender.com"]
   ```
   *(use your actual frontend URL)*
3. Save and redeploy

---

## 🔄 **Auto-Deploy on Push**

Render automatically redeploys when you push to your branch! Just:

```bash
git add .
git commit -m "Your changes"
git push
```

Both services will auto-update.

---

## 💰 **Cost Breakdown**

### Free Tier (Recommended for Testing)
- **Backend**: Free (spins down after 15 min of inactivity)
- **Frontend**: Free (always on)
- **Total**: $0/month
- **Trade-off**: First request after idle takes ~30-60 seconds

### Always-On (Recommended for Production)
- **Backend**: $7/month (Starter plan)
- **Frontend**: Free (always on)
- **Total**: $7/month
- **Benefit**: Instant responses, no cold starts

### Storage
- **Included**: 1GB free persistent disk (if you upgrade to paid backend)
- **Free tier**: Uses `/tmp` (files deleted on restart)

---

## 🐛 **Troubleshooting**

### **Backend Issues**

**Logs**: Render Dashboard → Backend Service → "Logs" tab

Common issues:
- `ModuleNotFoundError`: Check `requirements.txt` has all dependencies
- `401 Unauthorized`: Check `ANTHROPIC_API_KEY` is set correctly
- `Port binding error`: Make sure start command uses `$PORT`

### **Frontend Issues**

**Build Failed**:
- Check `npm install` succeeds locally
- Verify `frontend/package.json` exists
- Check build command: `npm run build`

**API Connection Error**:
- Verify `VITE_API_URL` is set correctly
- Check backend URL is accessible
- Update `BACKEND_CORS_ORIGINS` with frontend URL

### **CORS Errors**

If you see "CORS policy" errors in browser console:
1. Go to Backend service → Environment
2. Update `BACKEND_CORS_ORIGINS`:
   ```
   ["https://deep-doc-frontend.onrender.com"]
   ```
3. Redeploy backend

### **Cold Starts (Free Tier)**

Free tier services spin down after 15 minutes. First request takes 30-60s.

**Solutions**:
- Upgrade to Starter ($7/mo) for always-on
- Use a ping service (e.g., UptimeRobot) to keep it warm
- Accept the trade-off for free tier

---

## 📊 **Monitoring**

**Check Status**:
- Backend: `https://your-backend.onrender.com/health`
- Status API: `https://your-backend.onrender.com/api/v1/status`

**Logs**:
- Real-time logs in Render dashboard
- Filter by error/warning levels

---

## 🔐 **Security Best Practices**

1. **Never commit API keys** to git
2. **Use environment variables** for secrets
3. **Update CORS** to only allow your frontend domain
4. **Enable HTTPS** (automatic on Render)
5. **Rotate API keys** regularly

---

## 🚀 **Scaling**

When you outgrow free tier:

1. **Upgrade Backend**: Free → Starter ($7) → Professional ($25)
2. **Add Persistent Disk**: For file uploads (1GB free)
3. **Add Redis**: For caching (optional)
4. **Add Database**: PostgreSQL if needed later

---

## 📝 **Environment Variables Reference**

### Backend
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxx
CLAUDE_MODEL=claude-sonnet-4-20250514
LLM_PROVIDER=claude

# Optional
BACKEND_CORS_ORIGINS=["https://your-frontend.onrender.com"]
UPLOAD_DIR=/tmp/uploads
MAX_FILE_SIZE=52428800
PYTHONUNBUFFERED=1
```

### Frontend
```bash
# Required
VITE_API_URL=https://your-backend.onrender.com/api/v1
```

---

## 🎯 **Success Checklist**

- [ ] Backend deployed and healthy (`/health` returns 200)
- [ ] Frontend deployed and loads
- [ ] Can upload Excel file
- [ ] Can chat with Claude
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] API key working

---

## 🆘 **Need Help?**

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Check Logs**: Dashboard → Service → Logs tab

---

**Estimated Time**: 20-30 minutes for first deployment

**Next Steps**: Test your app, monitor usage, upgrade to always-on if needed!
