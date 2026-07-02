{% extends "mail_templated/base.tpl" %}

{% block subject %}
Reset Your AlphaCMMS Password
{% endblock %}

{% block body %}
Hello {{ first_name }},

We received a request to reset your password for your AlphaCMMS account.

Click the link below to set a new password:

{{ url }}

This link will expire in 24 hours. If you did not request a password reset, you can safely ignore this email — your password will remain unchanged.

Best regards,
The AlphaCMMS Team
{% endblock %}

{% block html %}
<html>
<head>
  <style>
    body {
      font-family: Arial, sans-serif;
      color: #333;
    }
    .highlight {
      color: #2b553a;
    }
    a.button {
      background-color: #2b553a;
      color: white;
      padding: 10px 20px;
      text-decoration: none;
      border-radius: 4px;
      display: inline-block;
      margin-top: 10px;
    }
    .note {
      font-size: 12px;
      color: #888;
      margin-top: 20px;
    }
  </style>
</head>
<body>
  <p class="highlight"><strong>Hello {{ first_name }},</strong></p>

  <p>We received a request to reset your password for your <strong>AlphaCMMS</strong> account.</p>

  <p>Click the button below to set a new password:</p>

  <p><a class="button" href="{{ url }}">Reset Password</a></p>

  <p>Or copy and paste this link into your browser:</p>
  <p><a href="{{ url }}">{{ url }}</a></p>

  <p class="note">This link will expire in 24 hours. If you did not request a password reset, you can safely ignore this email.</p>

  <p class="highlight">Best regards,<br>The AlphaCMMS Team</p>
</body>
</html>
{% endblock %}
