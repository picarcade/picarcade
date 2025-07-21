# Authentication Issues & Resolutions

## Issue #1: Google OAuth PKCE Flow Failure

**Problem:**
```
error: "invalid request: both auth code and code verifier should be non-empty"
code: "missing"
```

**Root Cause:** 
- Custom `/auth/callback/route.ts` was intercepting Supabase's automatic PKCE flow
- Conflicted with `detectSessionInUrl: true` setting
- Backend couldn't validate OAuth tokens due to incorrect `set_session()` usage

**Resolution:**
1. **Removed custom callback route** - Let Supabase handle OAuth automatically
2. **Fixed Supabase client config:**
   ```typescript
   // frontend/app/lib/supabase.ts
   export const supabase = createClient(url, key, {
     auth: {
       flowType: 'pkce',
       detectSessionInUrl: true // Let Supabase handle OAuth callbacks
     }
   })
   ```
3. **Simplified OAuth initiation:**
   ```typescript
   // Remove custom redirectTo, let Supabase handle it
   await supabase.auth.signInWithOAuth({
     provider: 'google',
     // No custom redirectTo URL
   })
   ```

## Issue #2: Backend Token Validation Error

**Problem:**
```
[DEBUG AUTH] ❌ New auth method failed: AttributeError: 'dict' object has no attribute 'headers'
```

**Root Cause:**
- Backend calling `set_session(access_token, None)` 
- Supabase's `set_session()` requires both access_token AND refresh_token
- Passing `None` for refresh_token caused the error

**Resolution:**
```python
# app/services/session_manager.py - BEFORE (broken):
user_supabase.auth.set_session(access_token, None)
user_response = user_supabase.auth.get_user()

# AFTER (fixed):
user_response = user_supabase.auth.get_user(jwt=access_token)
```

## Issue #3: API Authentication Failure

**Problem:**
- OAuth login worked but API calls returned 401 Unauthorized
- Frontend wasn't sending proper authentication headers

**Root Cause:**
- Frontend successfully got Supabase OAuth tokens
- Backend token validation fell back to Method 2 (admin client) instead of Method 1
- API interceptor was working but token validation was inefficient

**Resolution:**
1. **Fixed Method 1 token validation** (primary fix)
2. **Method 2 remained as fallback** (admin client validation)
3. **Added comprehensive debugging** to identify validation flow

## Issue #4: Sign-Out Failures

**Problem:**
```
DELETE /api/v1/generation/session/... 405 (Method Not Allowed)
POST .../auth/v1/logout 403 (Forbidden)
AuthSessionMissingError: Auth session missing!
```

**Root Cause:**
1. Frontend used raw `fetch()` without auth headers for session cleanup
2. OAuth sessions sometimes can't logout through Supabase when corrupted

**Resolution:**
1. **Fixed session cleanup:**
   ```typescript
   // BEFORE (broken):
   await fetch(`/api/v1/generation/session/${sessionId}`, { method: 'DELETE' })
   
   // AFTER (fixed):
   const { clearSession } = await import('../lib/api')
   await clearSession(sessionId) // Uses authenticated API client
   ```

2. **Enhanced signOut with fallback:**
   ```typescript
   // Try Supabase logout, fallback to local cleanup
   const { error } = await supabase.auth.signOut()
   if (error) {
     // Force local session cleanup
     setUser(null)
     setSession(null)
     localStorage.clear() // Clear all auth tokens
   }
   ```

## Key Lessons

1. **Don't interfere with Supabase PKCE flow** - Let `detectSessionInUrl: true` handle it
2. **Use correct Supabase API methods** - `get_user(jwt=token)` not `set_session(token, None)`
3. **Always use authenticated API clients** - Don't mix raw `fetch()` with auth-required endpoints
4. **Implement fallback auth cleanup** - OAuth sessions can become corrupted
5. **Add comprehensive debugging** - Authentication flows are complex and need visibility

## Files Modified

- `frontend/app/lib/supabase.ts` - Fixed PKCE configuration
- `app/services/session_manager.py` - Fixed token validation methods  
- `frontend/app/components/PerplexityInterface.tsx` - Fixed session cleanup
- `frontend/app/components/AuthProvider.tsx` - Enhanced signOut handling
- `frontend/app/lib/api.ts` - Added clearSession function
- **Deleted:** `frontend/app/auth/callback/route.ts` - Removed conflicting custom callback 