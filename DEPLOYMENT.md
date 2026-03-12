# 🚀 Production Deployment Guide

## Quick Setup for Render/Vercel Deployment

### Step 1: Deploy the Backend (Render)
1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard:
   ```
   DATABASE_URL=your_postgres_database_url
   SECRET_KEY=your_django_secret_key
   DEBUG=False
   ALLOWED_HOSTS=your-render-domain.onrender.com,localhost
   ```

### Step 2: Deploy the Frontend (Vercel)
1. Connect your GitHub repository to Vercel
2. Set environment variable:
   ```
   REACT_APP_API_URL=https://your-render-domain.onrender.com/api
   ```

### Step 3: Run Production Setup
After deployment, run the production setup script to create facilities and users:

```bash
# SSH into your Render server or run locally with production DB
python setup_production.py
```

### Step 4: Test the System
1. **Patient Submission**: Go to your Vercel URL and submit patient data
2. **Facility Login**: Use these credentials:
   - **Kampala Referral Hospital**: `kampala_staff` / `kampala123`
   - **Mulago National Hospital**: `mulago_staff` / `mulago123`
   - **Luwero General Hospital**: `luwero_staff` / `luwero123`

### District Coverage
- **Kampala Referral Hospital**: Kampala, Wakiso, Mpigi
- **Mulago National Hospital**: Kampala, Mukono, Buikwe
- **Luwero General Hospital**: Luwero, Nakasongola, Kayunga

### Troubleshooting
- **403 Login Error**: Run `python setup_production.py` to create users
- **500 Server Error**: Check that DATABASE_URL is correctly configured
- **CORS Issues**: Ensure your frontend URL is in ALLOWED_HOSTS

### Admin Access
- **Username**: `admin`
- **Password**: `admin123`
- **URL**: `/admin/` or `/harakacare-admin/`

## 🎯 System Features
✅ Patient triage with AI risk assessment
✅ Automatic facility routing by district
✅ Real-time facility dashboards
✅ Emergency case prioritization
✅ Multi-district coverage (8 districts total)

The system is now ready for production use!
