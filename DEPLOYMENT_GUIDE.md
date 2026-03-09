# 🚀 HarakaCare Deployment Guide

## 📋 Overview
Deploy HarakaCare with:
- **Backend**: Railway (Django + PostgreSQL)
- **Frontend**: Vercel (React)

---

## 🔧 Backend Deployment (Railway)

### 1. Prepare Repository
```bash
# Your code is already ready with:
✓ railway.toml configuration
✓ Procfile for deployment
✓ Production settings
✓ Updated requirements.txt
```

### 2. Deploy to Railway
1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Select `harakacare` project
4. Railway will automatically detect Django project

### 3. Set Environment Variables in Railway
```bash
# Required Environment Variables:
DJANGO_SETTINGS_MODULE=harakacare.settings.production
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=.railway.app,localhost,127.0.0.1

# CORS - IMPORTANT: Add your Vercel domain!
CORS_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app,https://localhost:3000

# Database (Railway provides automatically)
DATABASE_URL=${{RAILWAY_DATABASE_URL}}

# Optional: S3 for static files
USE_S3=True
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### 4. Deploy Commands
Railway will automatically:
- Install dependencies from `requirements.txt`
- Run migrations
- Start server with Gunicorn

---

## 🎨 Frontend Deployment (Vercel)

### 1. Prepare Repository
```bash
# Your code is already ready with:
✓ vercel.json configuration
✓ Updated package.json
✓ API URL configured for production
```

### 2. Deploy to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Connect your GitHub repository
3. Select `frontend` folder as root directory
4. Vercel will detect React app

### 3. Set Environment Variables in Vercel
```bash
# Add your Railway backend URL:
REACT_APP_API_URL=https://your-railway-app.railway.app/api
```

### 4. Deploy
Vercel will automatically:
- Install dependencies
- Build React app
- Deploy to global CDN

---

## 🔗 Important API Connections

### ✅ What's Already Configured:

1. **Frontend API Calls** (`api.js`):
   ```javascript
   // Uses environment variable or fallback
   const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';
   ```

2. **CORS Settings** (Backend):
   ```python
   # Production CORS will use your Vercel domain
   CORS_ALLOWED_ORIGINS = [
       'https://your-vercel-domain.vercel.app',
       'https://localhost:3000'
   ]
   ```

3. **Authentication**:
   - Session-based auth with `withCredentials: true`
   - Cross-origin cookies configured

4. **API Endpoints** (All working):
   - `/api/v1/triage/{patientToken}/submit/` - Patient triage
   - `/api/facilities/auth/login/` - Facility login
   - `/api/facilities/cases/` - Facility cases
   - Automatic booking endpoints

---

## ⚠️ Critical Deployment Steps

### 1. Update CORS Origins
After deploying to Vercel, update Railway environment variables:
```bash
CORS_ALLOWED_ORIGINS=https://your-actual-vercel-domain.vercel.app
```

### 2. Update Frontend API URL
After deploying to Railway, update Vercel environment variables:
```bash
REACT_APP_API_URL=https://your-actual-railway-domain.railway.app/api
```

### 3. Test the Connection
1. Deploy both services
2. Test patient triage submission
3. Test facility dashboard login
4. Verify automatic booking works

---

## 🎯 Features Ready for Production

✅ **Automatic Booking Confirmation**
- High-risk patients get instant confirmation
- Dashboard shows auto-confirmed status
- All API endpoints working

✅ **Facility Dashboard**
- Login/authentication
- Case management
- Filtering and search
- Auto-confirmed indicators

✅ **Patient Triage**
- Symptom assessment
- Risk classification
- Red flag detection
- Automatic routing

---

## 🚨 Troubleshooting

### CORS Issues
- Make sure Vercel domain is in Railway CORS settings
- Check that `withCredentials: true` is maintained

### Database Issues
- Railway automatically provides PostgreSQL
- Check `DATABASE_URL` is set correctly

### Static Files
- Use S3 for production (recommended)
- Or configure Whitenoise for basic static file serving

---

## 🎉 You're Ready!

Your HarakaCare application is fully configured and ready for production deployment!

**Backend**: Railway → **Frontend**: Vercel → **Connected**: ✅
