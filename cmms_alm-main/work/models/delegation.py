"""
Cover while away: a named signer (APPROVER, CLIENT rep, HEAD OF FINANCE & TREASURY)
names a stand-in for a period. During it the stand-in may act on the signer's
named steps; every such action is stamped "on behalf of" the signer.

Rules: the stand-in holds the same role; nobody stands in for themselves; a person
who is away cannot be a stand-in; cover cannot be passed on (a stand-in acts only
for the signer, never for whoever the signer covers); one cover per person at a time.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Roles whose holders can be named signers, and so may need cover.
SIGNER_ROLES = ('APPROVER', 'CLIENT', 'HEAD OF FINANCE & TREASURY')


class DelegationQuerySet(models.QuerySet):
    def active(self, at=None):
        at = at or timezone.now()
        return self.filter(starts_at__lte=at, ends_at__gt=at, ended_early_at__isnull=True)

    def overlapping(self, starts_at, ends_at):
        return self.filter(starts_at__lt=ends_at, ends_at__gt=starts_at, ended_early_at__isnull=True)


class Delegation(models.Model):
    person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='covers_given',
                               help_text="The signer who is away.")
    stand_in = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='covers_taken',
                                 help_text="Who acts for them meanwhile.")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    value_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True,
                                      help_text="Optional: amounts above this still wait for the person.")
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    ended_early_at = models.DateTimeField(null=True, blank=True)
    ended_early_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='+')

    objects = DelegationQuerySet.as_manager()

    class Meta:
        ordering = ['-starts_at']
        verbose_name = "Cover while away"
        verbose_name_plural = "Cover while away"

    def __str__(self):
        return f"{self.stand_in} covers {self.person} from {self.starts_at:%d %b} to {self.ends_at:%d %b %Y}"

    @property
    def status(self):
        now = timezone.now()
        if self.ended_early_at:
            return 'ended_early'
        if now < self.starts_at:
            return 'scheduled'
        if now >= self.ends_at:
            return 'ended'
        return 'active'

    def clean(self):
        errors = {}
        person, stand_in = self.person, self.stand_in
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors['ends_at'] = "The end must be after the start."
        if person and person.roles not in SIGNER_ROLES:
            errors['person'] = "Only signers (APPROVER, CLIENT, HEAD OF FINANCE & TREASURY) need cover."
        if person and stand_in:
            if person.pk == stand_in.pk:
                errors['stand_in'] = "Choose someone else to stand in."
            elif not stand_in.is_active:
                errors['stand_in'] = "The stand-in is inactive."
            elif stand_in.roles != person.roles:
                errors['stand_in'] = f"The stand-in must also hold the {person.roles} role."
        if not errors and self.starts_at and self.ends_at:
            others = Delegation.objects.exclude(pk=self.pk).overlapping(self.starts_at, self.ends_at)
            if others.filter(person=person).exists():
                errors['starts_at'] = "This person already has cover for part of this period."
            elif others.filter(person=stand_in).exists():
                errors['stand_in'] = "The stand-in is away themselves during this period."
            elif others.filter(stand_in=person).exists():
                errors['person'] = "This person is standing in for someone then; cover cannot be passed on."
        if errors:
            raise ValidationError(errors)

    def end_early(self, user):
        self.ended_early_at = timezone.now()
        self.ended_early_by = user
        self.save(update_fields=['ended_early_at', 'ended_early_by'])


def active_cover_for(person, stand_in, at=None):
    """The active cover in which `stand_in` acts for `person`, if any."""
    return Delegation.objects.active(at).filter(person=person, stand_in=stand_in).first()
