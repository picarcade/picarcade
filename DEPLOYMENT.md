# Deployment Configuration Guide

This document explains how to properly configure the PicArcade application for production deployment.

## Issues Fixed

### XP Loading Issue (January 2025)
- **Problem**: Users' XP wasn't loading on production login due to ResponseValidationError
- **Cause**: API endpoint returned `None` instead of proper response for users without subscription tiers
- **Fix**: Updated `/api/v1/subscriptions/current` endpoint to handle users with XP but no tier assignment
- **Commit**: `bb381da` - "Fix XP loading issue for users without subscription tiers"

### Frontend API Connection Issue
- **Problem**: Frontend tries to connect to `localhost:8000` in production
- **Cause**: Environment variable `NEXT_PUBLIC_API_URL` not set in production
- **Solution**: Configure environment variables in deployment platform

## Production Environment Variables

### Backend (FastAPI) - Render/Railway Deployment
Set these environment variables in your backend hosting platform:

```bash
# Supabase Configuration
SUPABASE_URL=https://izfjglgvaqrqaywfniwi.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# API Keys
OPENAI_API_KEY=your_openai_key
REPLICATE_API_TOKEN=your_replicate_token
RUNWAY_API_KEY=your_runway_key
GOOGLE_API_KEY=your_google_key

# Stripe (Production Keys)
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application Settings
FRONTEND_URL=https://picarcade.ai
DEBUG=False
```

### Frontend (Next.js) - Vercel Deployment

**CRITICAL**: Set these in your Vercel dashboard under Project Settings > Environment Variables:

```bash
# Backend API URL - THIS FIXES THE XP LOADING ISSUE
NEXT_PUBLIC_API_URL=https://api.picarcade.ai

# Supabase Configuration  
NEXT_PUBLIC_SUPABASE_URL=https://izfjglgvaqrqaywfniwi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Stripe (Production Keys)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...

# Optional: Production domain
NEXT_PUBLIC_PRODUCTION_URL=https://picarcade.ai
```

## Deployment Steps

1. **Backend Deployment**:
   - Deploy to Render/Railway with the environment variables above
   - Ensure the API is accessible at `https://api.picarcade.ai`

2. **Frontend Deployment**:
   - Set environment variables in Vercel dashboard
   - Deploy from main branch
   - Verify XP loading works after login

3. **Verification**:
   - Test login on production
   - Verify XP balance loads correctly
   - Check browser console for no `localhost:8000` errors

## Domain Configuration

- **Frontend**: `https://picarcade.ai`
- **Backend API**: `https://api.picarcade.ai`
- **Database**: Supabase hosted

## Common Issues

1. **XP Not Loading**: Check that `NEXT_PUBLIC_API_URL` is set correctly in Vercel
2. **CORS Errors**: Ensure frontend domain is included in backend CORS configuration
3. **Authentication Issues**: Verify Supabase keys match between frontend and backend

## Recent Fixes Applied

- ✅ Fixed ResponseValidationError in subscription endpoint
- ✅ Added proper handling for users without subscription tiers  
- ✅ Updated environment configuration documentation
- 🔄 **Next**: Set `NEXT_PUBLIC_API_URL=https://api.picarcade.ai` in Vercel dashboard 