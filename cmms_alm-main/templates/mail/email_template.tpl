{% extends "mail_templated/base.tpl" %}

{% block subject %}
Welcome to Our Service, {{ first_name }}!
{% endblock %}

{% block body %}
Hello {{ first_name }},

Thank you for registering with us. We're excited to have you on board and look forward to providing you with the best experience possible.

To activate your account, please use the OTP code below:

OTP Code: {{ code}}

Please enter this code on the verification page to confirm your email address and complete your registration.

If the OTP code does not work, please ensure you have entered it exactly as shown without any spaces or contact us for assistance.

If you have any questions or need further assistance, please don't hesitate to reach out.

Welcome aboard!

Best regards,
The Team
{% endblock %}

{% block html %}
<html>
<head>
  <style>
    /* Add any specific style you want here. */
  </style>
</head>
<body>
  <p>Hello <strong>{{ first_name }}</strong>,</p>

  <p>Thank you for registering with us. We're excited to have you on board and look forward to providing you with the best experience possible.</p>

  <p>To activate your account, please use the OTP code below:</p>

  <p><strong>OTP Code: {{ code }}</strong></p>

  <p>Please enter this code on the verification page to confirm your email address and complete your registration.</p>

  <p>If the OTP code does not work, please ensure you have entered it exactly as shown without any spaces or contact us for assistance.</p>

  <p>If you have any questions or need further assistance, please don't hesitate to reach out.</p>

  <p>Welcome aboard!</p>

  <p>Best regards,<br>
  The Team</p>
</body>
</html>
{% endblock %}