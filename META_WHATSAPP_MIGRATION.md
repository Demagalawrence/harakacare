# Meta WhatsApp Cloud API Migration Guide

## Overview
This guide helps migrate HarakaCare from 360Dialog to Meta WhatsApp Cloud API for better native WhatsApp features and cost efficiency.

## Key Benefits
- **Native Interactive Buttons**: Better UX than numbered menus
- **Location Pin Support**: Direct location sharing from WhatsApp
- **List Messages**: Multi-select menus for chronic conditions
- **Lower Costs**: Direct Meta API pricing vs third-party markup
- **Better Reliability**: Direct integration with WhatsApp platform

## Migration Steps

### 1. Meta Developer Setup

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create new app or use existing WhatsApp Business App
3. Get these credentials:
   - **Access Token** (permanent or system user)
   - **Phone Number ID** (from WhatsApp settings)
   - **Webhook Verify Token** (your choice)
   - **App Secret** (for webhook signature)

### 2. Update Django Settings

Add to your `settings/production.py` or `.env` file:

```python
# Meta WhatsApp Cloud API
META_WHATSAPP_ACCESS_TOKEN = "your_access_token_here"
META_WHATSAPP_PHONE_NUMBER_ID = "your_phone_number_id_here"  
META_WHATSAPP_WEBHOOK_VERIFY_TOKEN = "harakacare_meta_verify"
META_WHATSAPP_APP_SECRET = "your_app_secret_here"
META_WHATSAPP_BASE_URL = "https://graph.facebook.com"

# Optional: Remove 360Dialog credentials
# THREESIXTY_DIALOG_API_KEY = ""
# THREESIXTY_DIALOG_WEBHOOK_SECRET = ""
# THREESIXTY_DIALOG_VERIFY_TOKEN = ""
```

### 3. Webhook Configuration

In Meta Developers Dashboard:

**Webhook URL**: `https://yourdomain.com/messaging/whatsapp/meta/webhook/`

**Settings**:
- Method: POST
- Events to subscribe: `messages`, `message_status`
- Verify Token: `harakacare_meta_verify` (match your setting)
- App Secret: Add your app secret for signature verification

### 4. Update Code Integration

#### Option A: Gradual Migration (Recommended)

Keep both endpoints running during transition:

```python
# In your main webhook handler
if request.path.endswith('/meta/webhook/'):
    # Use new Meta handler
    from apps.messaging.whatsapp.meta_whatsapp_views import MetaWhatsAppWebhookView
    return MetaWhatsAppWebhookView.as_view()(request)
else:
    # Fallback to 360Dialog
    from apps.messaging.whatsapp.whatsapp_views import WhatsAppWebhookView
    return WhatsAppWebhookView.as_view()(request)
```

#### Option B: Direct Switch

Update URLs to use Meta webhook:

```python
# apps/messaging/whatsapp/urls.py
urlpatterns = [
    path("meta/webhook/", MetaWhatsAppWebhookView.as_view(), name="meta_webhook"),
    # Comment out or remove 360dialog webhook
    # path("webhook/", WhatsAppWebhookView.as_view(), name="webhook"),
]
```

### 5. Test Migration

1. **Webhook Verification**: 
   - Meta will send GET request with `hub.challenge`
   - Should return the challenge value

2. **Message Test**:
   - Send test message to your WhatsApp number
   - Check logs for proper parsing

3. **Interactive Buttons Test**:
   - Should trigger age/sex gate with buttons
   - Test button responses like "1A", "6B"

4. **Location Test**:
   - Send location request message
   - Share location pin from WhatsApp

### 6. Production Deployment

1. Update webhook URL in Meta Dashboard
2. Test with Meta's webhook tester
3. Monitor logs for errors
4. Remove 360Dialog credentials after successful testing

## New Features Enabled

### Interactive Buttons
```python
# Automatic conversion of menus to buttons
response = _format_as_interactive_buttons(message)
# Returns: {"type": "interactive_buttons", "buttons": [...]}
```

### Location Requests
```python
# Request user's GPS location
response = _format_location_request("Please share your location")
# Returns: {"type": "location_request", "message": "..."}
```

### List Messages (Future)
```python
# For chronic conditions multi-select
meta_whatsapp_client.send_list_message(
    to=phone,
    header="Select Conditions",
    body_text="Choose all that apply:",
    button_text="View Options",
    sections=[{
        "title": "Common Conditions",
        "rows": [
            {"id": "diabetes", "title": "🩸 Diabetes"},
            {"id": "hypertension", "title": "🩺 Hypertension"},
            # ...
        ]
    }]
)
```

## Troubleshooting

### Common Issues

**403 Signature Verification Failed**
- Check `META_WHATSAPP_APP_SECRET` matches dashboard
- Ensure webhook secret is properly set

**400 Bad Request**
- Verify phone number ID format
- Check access token permissions

**Buttons Not Working**
- Ensure using `meta_whatsapp_handler` in views
- Check message type is `interactive_buttons`

**Location Not Received**
- User must share location, not just coordinates
- Check `message_type='location'` handling

### Monitoring

Add these log patterns to monitor:

```python
# Meta webhook success
logger.info("Meta WhatsApp webhook received: ...")

# Interactive button clicks  
logger.info("Button reply from {}: {} - {}".format(phone, button_id))

# Location shares
logger.info("Location from {}: {}, {}".format(phone, latitude, longitude))

# API errors
logger.error("Meta API request failed: {}".format(error))
```

## Rollback Plan

If issues occur, rollback steps:

1. Update webhook URL back to 360Dialog endpoint
2. Restore 360Dialog credentials in settings
3. Test legacy functionality
4. Investigate Meta API issues separately

## Support

- **Meta Documentation**: https://developers.facebook.com/docs/whatsapp/
- **WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp/business-api/
- **Graph API Explorer**: https://developers.facebook.com/tools/explorer/

## Timeline

- **Week 1**: Setup Meta Developer app, get credentials
- **Week 2**: Deploy new webhook endpoints, test functionality  
- **Week 3**: Gradual traffic migration (50% Meta, 50% 360Dialog)
- **Week 4**: Full migration, remove 360Dialog
- **Week 5**: Monitor and optimize

## Success Metrics

Track these metrics during migration:

- **Message Delivery Rate**: Should improve with direct API
- **Response Time**: Should decrease with native features
- **User Engagement**: Should increase with interactive buttons
- **Error Rate**: Should decrease with direct integration
- **Cost**: Should reduce with direct Meta pricing

## Security Notes

- Always use HTTPS for webhook URLs
- Verify webhook signatures with app secret
- Store credentials securely (environment variables)
- Monitor for unusual webhook activity
- Rate limit inbound message processing
