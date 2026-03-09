# Meta WhatsApp Cloud API Credentials Setup Guide

## Overview
This guide shows exactly what credentials you need and where to get them for HarakaCare's Meta WhatsApp Cloud API integration.

## Required Credentials

### 1. Access Token (Permanent)
**Purpose**: Authentication for API calls
**Where to get**: Meta Developers Dashboard → Your App → WhatsApp → Settings
**Format**: Long alphanumeric string
**Setting name**: `META_WHATSAPP_ACCESS_TOKEN`

### 2. Phone Number ID  
**Purpose**: Identifies your WhatsApp Business phone number
**Where to get**: Meta Developers Dashboard → WhatsApp → Phone Numbers
**Format**: Numeric string (e.g., "123456789012345")
**Setting name**: `META_WHATSAPP_PHONE_NUMBER_ID`

### 3. Webhook Verify Token
**Purpose**: Verifies webhook ownership during setup
**Where to get**: Your choice - create any secure token
**Format**: String (e.g., "harakacare_meta_verify")
**Setting name**: `META_WHATSAPP_WEBHOOK_VERIFY_TOKEN`

### 4. App Secret
**Purpose**: Signs webhook requests for security
**Where to get**: Meta Developers Dashboard → Your App → Settings → Basic
**Format**: Long alphanumeric string
**Setting name**: `META_WHATSAPP_APP_SECRET`

## Step-by-Step Setup

### Step 1: Create Meta Developer Account
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Sign in with your Facebook account
3. Accept terms if prompted

### Step 2: Create WhatsApp Business App
1. In Meta Dashboard, click "Create App"
2. Choose "Business" app type
3. Select "WhatsApp" product
4. Name your app (e.g., "HarakaCare WhatsApp")
5. Choose "Business" account type

### Step 3: Get Phone Number ID
1. In your app dashboard, go to "WhatsApp" section
2. Click "Phone Numbers" or "Add Phone Number"
3. Add or select your WhatsApp Business number
4. **Copy the Phone Number ID** (looks like: 123456789012345)
5. Save this value

### Step 4: Get Access Token
1. In WhatsApp section, go to "Settings"
2. Scroll to "Access Token" section
3. Click "Generate" or "Add" new token
4. Choose **System User** token type (recommended for backend)
5. Set appropriate permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
6. **Copy the generated token** (starts with "EAA...")
7. Save immediately - tokens expire if not saved

### Step 5: Get App Secret
1. In app dashboard, go to "Settings" → "Basic"
2. Find "App Secret" field
3. Click "Show" to reveal the secret
4. **Copy the App Secret** (long string)
5. Store securely - this is critical for webhook security

### Step 6: Configure Webhook
1. In WhatsApp settings, go to "Webhooks"
2. Add webhook URL: `https://yourdomain.com/messaging/whatsapp/meta/webhook/`
3. Set "Verify Token" to: `harakacare_meta_verify` (or your choice)
4. Subscribe to events:
   - ✅ `messages`
   - ✅ `message_status`
5. Save configuration

## Environment Variables Configuration

Add these to your `.env` file or Django settings:

```bash
# Meta WhatsApp Cloud API Credentials
META_WHATSAPP_ACCESS_TOKEN="EAA......"  # From Step 4
META_WHATSAPP_PHONE_NUMBER_ID="123456789012345"  # From Step 3
META_WHATSAPP_WEBHOOK_VERIFY_TOKEN="harakacare_meta_verify"  # From Step 6
META_WHATSAPP_APP_SECRET="your_app_secret_here"  # From Step 5
META_WHATSAPP_BASE_URL="https://graph.facebook.com"  # Production URL
```

## Important Links

### Meta Developer Dashboard
- **Main Dashboard**: https://developers.facebook.com/
- **Your Apps**: https://developers.facebook.com/apps
- **WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp/business-api/

### Direct Links to Your App
Once you create your app, replace `YOUR_APP_ID` with your actual app ID:
- **App Dashboard**: https://developers.facebook.com/apps/YOUR_APP_ID/dashboard/
- **WhatsApp Settings**: https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp/
- **Webhook Configuration**: https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp/webhooks/
- **Settings**: https://developers.facebook.com/apps/YOUR_APP_ID/settings/

### Graph API Explorer (for testing)
- **Explorer**: https://developers.facebook.com/tools/explorer/
- **Test Access Token**: Generate temporary tokens here for testing

## Security Best Practices

### Access Token Security
- ✅ Use **System User** tokens (not User tokens)
- ✅ Set **appropriate permissions only** (principle of least privilege)
- ✅ **Rotate tokens regularly** (every 90 days recommended)
- ✅ **Store in environment variables**, not code
- ✅ **Use different tokens** for dev/staging/production

### Webhook Security
- ✅ **Use HTTPS** for webhook URL
- ✅ **Keep App Secret secure** - never commit to git
- ✅ **Verify webhook signatures** in your code
- ✅ **Rate limit** webhook processing
- ✅ **Log webhook events** for monitoring

### Phone Number Security
- ✅ **Use verified WhatsApp Business number**
- ✅ **Enable two-factor authentication** on Meta account
- ✅ **Monitor phone number status** in dashboard
- ✅ **Keep number active** (WhatsApp deactivates unused numbers)

## Testing Your Setup

### 1. Webhook Verification
```bash
# Test if Meta can reach your webhook
curl -X GET "https://yourdomain.com/messaging/whatsapp/meta/webhook/?hub.verify_token=harakacare_meta_verify"
```

### 2. API Test
```python
# Test with Graph API Explorer
import requests

token = "YOUR_ACCESS_TOKEN"
phone_id = "YOUR_PHONE_NUMBER_ID"

url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(url, json={
    "messaging_product": "whatsapp",
    "to": "TEST_PHONE_NUMBER",
    "type": "text",
    "text": {"body": "Test message"}
})

print(response.json())
```

### 3. Send Test Message
1. Use Meta's "Test Message" feature in dashboard
2. Send to your own WhatsApp number
3. Check if webhook receives the message

## Troubleshooting

### Common Issues

**401 Unauthorized**
- Check access token is valid and not expired
- Verify token has correct permissions
- Ensure using System User token

**403 Forbidden**  
- Check webhook signature verification
- Verify App Secret matches dashboard
- Ensure webhook URL is accessible

**400 Bad Request**
- Check Phone Number ID format
- Verify message payload structure
- Ensure API version is correct (v18.0)

**Webhook Not Receiving**
- Check webhook URL is correct and HTTPS
- Verify webhook events are subscribed
- Check firewall/proxy settings

### Debug Mode
Add to Django settings for development:
```python
DEBUG = True
LOGGING = {
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'meta_whatsapp_debug.log',
        },
    },
    'loggers': {
        'apps.messaging.whatsapp': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## Production Checklist

Before going live:

- [ ] **Access Token**: Generated and saved securely
- [ ] **Phone Number ID**: Copied from dashboard  
- [ ] **App Secret**: Stored in environment variables
- [ ] **Webhook URL**: HTTPS and accessible
- [ ] **Verify Token**: Set in webhook configuration
- [ ] **Permissions**: Only required permissions granted
- [ ] **Testing**: All flows tested successfully
- [ ] **Monitoring**: Logging and error handling in place
- [ ] **Backup**: Legacy 360Dialog still functional during transition

## Support Resources

### Documentation
- **WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp/business-api/
- **Graph API Reference**: https://developers.facebook.com/docs/graph-api/
- **Webhook Guide**: https://developers.facebook.com/docs/graph-api/webhooks/

### Community Support
- **Meta Developers Group**: https://www.facebook.com/groups/developers/
- **Stack Overflow**: Use tags `facebook-graph-api` and `whatsapp-business-api`
- **Meta Bug Reports**: https://developers.facebook.com/bugs/

### Quick Reference

| Setting | Example | Where to Get |
|----------|---------|----------------|
| Access Token | `EAAZBlZA...` | App → WhatsApp → Settings |
| Phone ID | `123456789012345` | App → WhatsApp → Phone Numbers |
| Verify Token | `harakacare_meta_verify` | Your choice (webhook setup) |
| App Secret | `abcdef123456...` | App → Settings → Basic |
| Webhook URL | `https://domain.com/.../meta/webhook/` | You configure this |

## Next Steps After Setup

1. **Update Django settings** with the credentials
2. **Test webhook** using Meta's tester
3. **Send test messages** via Graph API Explorer
4. **Monitor logs** for any errors
5. **Gradual migration** - start with 10% traffic to Meta endpoint
6. **Performance monitoring** - track delivery rates and response times

---

**🎯 Result**: With these credentials properly configured, HarakaCare will have full Meta WhatsApp Cloud API functionality with interactive buttons, location sharing, and native WhatsApp features!
