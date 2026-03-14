from django.db import models
from django.conf import settings
from utils.models import Dated, Status, UserPrivModel

class BudgetSetting(Dated, Status, UserPrivModel, models.Model):
    """
    Represents a budget setting for a facility, department, and associated controls.
    """
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.CASCADE,
        related_name='budget_settings',
        help_text="Facility or location associated with the budget."
    )
    
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name='budget_settings',
        help_text="Department associated with the budget."
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Budget amount allocated."
    )
    
    start_date = models.DateField(
        help_text="Start date for the budget period."
    )
    
    end_date = models.DateField(
        help_text="End date for the budget period."
    )
    
    exceeded_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Percentage of budget that triggers a notification if exceeded."
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='budget_notifications',
        help_text="Users to notify when the budget is exceeded."
    )
    request_approval = models.BooleanField(
        default=False,
        help_text="Indicates if approval is required for the budget."
    )

    def __str__(self):
        return f"{self.facility.name} - {self.department.name} Budget"

    class Meta:
        verbose_name = "Budget Setting"
        verbose_name_plural = "Budget Settings"




class BudgetCategory(Dated, UserPrivModel, models.Model):
    """
    Represents a category and subcategory allocation within a budget setting.
    """
    budget_setting = models.ForeignKey(
        'BudgetSetting',
        on_delete=models.CASCADE,
        related_name='categories',
        help_text="The budget setting this category belongs to."
    )
    category = models.ForeignKey(
        'accounts.Category',
        on_delete=models.CASCADE,
        help_text="Main category for the budget allocation."
    )
    subcategory = models.ForeignKey(
        'accounts.SubCategory',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Subcategory under the main category."
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Allocated amount for this category."
    )

    def __str__(self):
        return f"{self.category.name} - {self.subcategory.name if self.subcategory else 'No Subcategory'}"

    class Meta:
        verbose_name = "Budget Category"
        verbose_name_plural = "Budget Categories"
