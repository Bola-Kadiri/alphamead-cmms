"""
Super Admin bulk upload of vendors / payees (e.g. EKEDC, LAWMA) with their
bank details.

Columns:
    name, type, phone, email, account_name, bank, account_number, currency, status

Only `name` is required, so a vendor list can be loaded before bank details
are collected. A vendor without bank details can be picked on work orders but
can't be paid (Raise Payment and disbursement both refuse it).

Matching:
- With an account number: a vendor already holding it is skipped if it has the
  same name, and reported as an error otherwise (account numbers are unique).
- Without one: a vendor with the same name is skipped.
- Re-uploading a name that exists without bank details, now with them, fills
  the missing details in ("updated"). Nothing that is already filled is changed.
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from utils.csv_import import RowError, read_csv_rows, run_import

from .models import Vendor

REQUIRED_COLUMNS = ['name']
TEMPLATE_HEADER = ['name', 'type', 'phone', 'email', 'account_name', 'bank', 'account_number', 'currency', 'status']
TEMPLATE_ROWS = [
    ['EKEDC', 'Company', '08000000000', 'billing@ekedc.example', 'EKEDC Collections', 'Zenith Bank', '1012345678', 'NGN', 'Active'],
    ['LAWMA', 'Company', '08000000001', '', '', '', '', 'NGN', 'Active'],
]

TYPES = {value.lower(): value for value, _ in Vendor.VENDOR_TYPE_CHOICES}
# Accept the code (NGN) or the label (Nigerian Naira).
CURRENCIES = {}
for _code, _label in Vendor.CURRENCY_CHOICES:
    CURRENCIES[_code.lower()] = _code
    CURRENCIES[str(_label).lower()] = _code
STATUSES = {'active': 'Active', 'inactive': 'Inactive'}
BANK_FIELDS = ('account_name', 'bank', 'account_number')


def clean_phone(value, notes):
    """Undo Excel's damage to phone numbers where it can be undone."""
    if not value:
        return ''
    if re.fullmatch(r'\d+(\.\d+)?[eE]\+\d+', value):
        notes.append(f"phone '{value}' was damaged by Excel and left blank")
        return ''
    if re.fullmatch(r'[789]\d{9}', value):
        # Nigerian mobile number that lost its leading 0.
        notes.append(f"phone {value} → 0{value}")
        return '0' + value
    if len(value) > 15:
        raise RowError("phone is longer than 15 characters.")
    return value


def import_vendors_from_csv(file_obj, owner=None, dry_run=True):
    rows = read_csv_rows(file_obj, REQUIRED_COLUMNS)
    seen_accounts = set()

    def handle_row(row_number, row):
        name = row.get('name', '')
        if not name:
            raise RowError("Missing: name.")
        if len(name) > 255:
            raise RowError("name is longer than 255 characters.")

        vendor_type = TYPES.get((row.get('type') or 'company').lower())
        if vendor_type is None:
            raise RowError(f"type must be one of: {', '.join(TYPES.values())}.")
        currency = CURRENCIES.get((row.get('currency') or 'NGN').lower())
        if currency is None:
            raise RowError("currency must be one of: NGN, USD, EUR, GBP.")
        status = STATUSES.get((row.get('status') or 'active').lower())
        if status is None:
            raise RowError("status must be Active or Inactive.")

        notes = []
        phone = clean_phone(row.get('phone', ''), notes)
        account_name = row.get('account_name', '')
        bank = row.get('bank', '')
        account_number = row.get('account_number', '') or None
        for value, limit, label in ((account_name, 255, 'account_name'), (bank, 255, 'bank'),
                                    (account_number or '', 20, 'account_number')):
            if len(value) > limit:
                raise RowError(f"{label} is longer than {limit} characters.")
        email = row.get('email') or None
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise RowError(f"'{email}' is not a valid email address.")

        if account_number:
            if account_number in seen_accounts:
                raise RowError(f"account_number {account_number} appears more than once in the file.")
            seen_accounts.add(account_number)
            existing = Vendor.objects.filter(account_number=account_number).first()
            if existing is not None:
                if existing.name.strip().lower() == name.lower():
                    return 'skipped', f"vendor '{existing.name}' already exists"
                raise RowError(f"account_number {account_number} is already used by vendor '{existing.name}'.")

        same_name = list(Vendor.objects.filter(name__iexact=name)[:2])
        if len(same_name) > 1:
            raise RowError(f"There are several vendors named '{name}'. Fix it in the admin, then upload again.")
        if same_name:
            existing = same_name[0]
            fill = {field: value for field, value in
                    (('account_name', account_name), ('bank', bank), ('account_number', account_number), ('phone', phone))
                    if value and not getattr(existing, field)}
            if not fill:
                return 'skipped', f"vendor '{existing.name}' already exists"
            for field, value in fill.items():
                setattr(existing, field, value)
            existing.save(update_fields=list(fill))
            return 'updated', f"vendor '{existing.name}': added {', '.join(fill)}"

        Vendor.objects.create(
            owner=owner, name=name, type=vendor_type, phone=phone, email=email,
            account_name=account_name, bank=bank, account_number=account_number,
            currency=currency, status=status,
        )
        detail = f"{bank} {account_number}" if account_number else "no bank details yet — can't be paid until added"
        message = f"add vendor '{name}' ({detail})"
        if notes:
            message += '; ' + '; '.join(notes)
        return 'created', message

    return run_import(rows, handle_row, dry_run)
