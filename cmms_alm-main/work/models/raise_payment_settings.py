from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models


class RaisePaymentApprovalSettings(models.Model):
    """
    Raise Payment route by amount (NGN; a bill in any other currency takes the full route):
      from `threshold`: Procurement & Store adds the PO and quotation before the Approver;
      from `final_approval_threshold`: the user whose email is `second_approver_email` gives
      the final approval after the Reviewer.
    Requester → [Procurement & Store] → Approver → Reviewer → [final approver].
    One row, edited by the Super Admin in Django admin, so none of it needs a code change.
    """

    threshold = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal('100000.00'),
        verbose_name="Procurement threshold",
        help_text="Bills of this amount (NGN) or more need Procurement & Store (PO and quotation).",
    )
    final_approval_threshold = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal('500000.00'),
        help_text="Bills of this amount (NGN) or more need the final approval of the second approver.",
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
        return (f"Procurement from NGN {self.threshold:,.2f}; final approval from "
                f"NGN {self.final_approval_threshold:,.2f} by {self.second_approver_email}")

    @classmethod
    def current(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

    def needs_procurement(self, amount, currency):
        if (currency or 'NGN') != 'NGN':
            return True
        return amount is not None and amount >= self.threshold

    def needs_second_approval(self, amount, currency):
        if (currency or 'NGN') != 'NGN':
            return True
        return amount is not None and amount >= self.final_approval_threshold

    def second_approver(self):
        return get_user_model().objects.filter(
            email__iexact=self.second_approver_email, is_active=True,
        ).first()
