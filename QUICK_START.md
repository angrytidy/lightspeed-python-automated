# 🚀 Quick Start Guide - Lightspeed OAuth Helper

## Super Simple Setup (3 Steps!)

### 1. Set Up Your Credentials
Create a `.env` file in this folder with your Lightspeed API credentials:

```env
LIGHTSPEED_RETAIL_CLIENT_ID=your_client_id_here
LIGHTSPEED_RETAIL_CLIENT_SECRET=your_client_secret_here
LIGHTSPEED_RETAIL_REDIRECT_URI=https://localhost:8080/callback
LIGHTSPEED_RETAIL_SCOPE=employee:all
```

### 2. Run Login (First Time Only)
Double-click: **`lightspeed-login.cmd`**

This will:
- ✅ Open your browser for Lightspeed authorization
- ✅ Capture your authorization code automatically  
- ✅ Save your login tokens securely
- ✅ Test the connection

### 3. Run Tasks (Anytime)
Double-click: **`lightspeed-task.cmd`**

This gives you a menu to:
- 📊 Get account information
- 📦 List products/items
- 🏷️ List categories
- 👥 List customers
- 🏪 Get shop information
- 🏭 List vendors
- 🔧 Make custom API calls
- 🔄 Refresh your login token

## That's It! 🎉

No command line knowledge needed. Just double-click the files!

---

## 🛠️ Advanced Usage (Command Line)

If you prefer command line:

```bash
# First time login
lsr-auth init

# Make API calls
lsr-auth call /API/V3/Account.json
lsr-auth call /API/V3/Item.json

# Refresh token when needed
lsr-auth refresh

# Check status
lsr-auth info
```

## 🆘 Troubleshooting

**Problem**: "Not authenticated" error  
**Solution**: Run `lightspeed-login.cmd` first

**Problem**: Browser security warning  
**Solution**: Click "Advanced" → "Proceed to localhost" (this is normal for local development)

**Problem**: "Configuration error"  
**Solution**: Check your `.env` file has all required credentials

**Problem**: Token expired  
**Solution**: Use option 9 in `lightspeed-task.cmd` to refresh, or re-run `lightspeed-login.cmd`
