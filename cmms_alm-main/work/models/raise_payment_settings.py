from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models


class RaisePaymentApprovalSettings(models.Model):
    """
    Raise Payment second approval: a bill at or above `threshold` (in NGN),
    or in any other currency, needs a final approval from the user whose
    email is `second_approver_email`, after the Reviewer. One row, edited by
    the Super Admin in Django admin, so neither needs a code change.
    """

    threshold = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal('1000000.00'),
        help_text="Bills of this amount (NGN) or more need the second approval.",
    )
    second_approver_email = models.EmailField(
        default='wole.olufore@alphamead.com',
        help_text="Email of the AlphaCMMS user who gives the second (final) approval.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Raise Payment approval setting"
        verbose_name_plural = "Raise Payment approval settings"

    def __str__(self):
        return f"Second approval from NGN {self.threshold:,.2f} by {self.second_approver_email}"

    @classmethod
    def current(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

    def needs_second_approval(self, amount, currency):
        if (currency or 'NGN') != 'NGN':
            return True
        return amount is not None and amount >= self.threshold

    def second_approver(self):
        return get_user_model().objects.filter(
            email__iexact=self.second_approver_email, is_active=True,
        ).first()
