# Email Configuration for Wine-AI

To enable email sending for tokens, add the following configuration to your `.env` file in the project root directory:

```
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=Wine AI <your-email@gmail.com>
EMAIL_USE_TLS=True
```

## Configuration Options

- `EMAIL_HOST`: Your SMTP server hostname
  - For Gmail: `smtp.gmail.com`
  - For Outlook/Hotmail: `smtp-mail.outlook.com`
  - For QQ Mail: `smtp.qq.com`
  - For 163 Mail: `smtp.163.com`

- `EMAIL_PORT`: SMTP server port
  - Usually 587 for TLS
  - 465 for SSL
  - 25 for unencrypted

- `EMAIL_USER`: Your email username/address

- `EMAIL_PASSWORD`: Your email password
  - For Gmail, you need to use an "App Password" (see instructions below)
  - For other providers, you might need to enable SMTP access in your account settings

- `EMAIL_FROM`: The "From" address displayed in emails
  - Can be formatted as `Name <email@example.com>`
  - Defaults to EMAIL_USER if not specified

- `EMAIL_USE_TLS`: Whether to use TLS encryption (True/False)
  - Should be set to True for most modern email servers

## Using Gmail

If you're using Gmail, you need to:

1. Enable 2-Step Verification on your Google account
2. Generate an App Password:
   - Go to your Google Account settings
   - Select "Security"
   - Under "Signing in to Google," select "App passwords"
   - Generate a new app password for "Mail" on "Other (Custom name)"
   - Use this generated password as your `EMAIL_PASSWORD`

## Troubleshooting

If emails are not being sent:

1. Check your server logs for specific error messages
2. Verify your email credentials are correct
3. Make sure your email provider allows SMTP access
4. Some providers might block access from unfamiliar locations - check your email for security alerts
5. If using Gmail, make sure you're using an App Password, not your regular password 