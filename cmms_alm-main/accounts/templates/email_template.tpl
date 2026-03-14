{% extends "mail_templated/base.tpl" %}

{% block subject %}
Welcome to Our Service, {{ first_name }}!
{% endblock %}

{% block body %}
Hello {{ first_name }},

Your account has been created successfully.

To set your password and complete onboarding, please follow the link below:

{{ url }}

We look forward to having you onboard. If you have any questions or need help, don’t hesitate to reach out.

Best regards,  
The Team
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
      padding: 10px 15px;
      text-decoration: none;
      border-radius: 4px;
      display: inline-block;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <p class="highlight"><strong>Hello {{ first_name }},</strong></p>

  <p>Your account has been created successfully.</p>

  <p>To set your password and complete onboarding, please follow the link below:</p>

  <p><a class="button" href="{{ url }}">Set Your Password</a></p>

  <p>Or copy and paste the following link into your browser:</p>
  <p><a href="{{ url }}</a></p>

  <p>We look forward to having you onboard. If you have any questions or need help, don’t hesitate to reach out.</p>

  <p class="highlight">Best regards,<br>
  The Team</p>
</body>
</html>
{% endblock %}
