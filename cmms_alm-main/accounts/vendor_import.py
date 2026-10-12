"""
Super Admin bulk upload of vendors / payees (e.g. EKEDC, LAWMA) with their
bank details.

Columns:
    name, type, phone, email, account_name, bank, account_number, currency, status

Only adds. A vendor whose account number already exists is skipped if it has
the same name, and reported as an error otherwise (account numbers are unique).
"""
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from utils.csv_import import RowError, read_csv_rows, run_import

from .models import Vendor

REQUIRED_COLUMNS = ['name', 'type', 'phone', 'account_name', 'bank', 'account_number', 'currency']
TEMPLATE_HEADER = ['name', 'type', 'phone', 'email', 'account_name', 'bank', 'account_number', 'currency', 'status']
TEMPLATE_ROWS = [
    ['EKEDC', 'Company', '08000000000', 'billing@ekedc.example', 'EKEDC Collections', 'Zenith Bank', '1012345678', 'NGN', 'Active'],
    ['LAWMA', 'Company', '08000000001', '', 'LAWMA Revenue', 'Access Bank', '0698765432', 'NGN', 'Active'],
]

TYPES = {value.lower(): value for value, _ in Vendor.VENDOR_TYPE_CHOICES}
CURRENCIES = {value for value, _ in Vendor.CURRENCY_CHOICES}
STATUSES = {'active': 'Active', 'inactive': 'Inactive'}


def import_vendors_from_csv(file_obj, owner=None, dry_run=True):
    rows = read_csv_rows(file_obj, REQUIRED_COLUMNS)
    seen_accounts = set()

    def handle_row(row_number, row):
        missing = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if missing:
            raise RowError(f"Missing: {', '.join(missing)}.")

        name = row['name']
        vendor_type = TYPES.get(row['type'].lower())
        if vendor_type is None:
            raise RowError(f"type must be one of: {', '.join(TYPES.values())}.")
        currency = row['currency'].upper()
        if currency not in CURRENCIES:
            raise RowError(f"currency must be one of: {', '.join(sorted(CURRENCIES))}.")
        status = STATUSES.get((row.get('status') or 'active').lower())
        if status is None:
            raise RowError("status must be Active or Inactive.")
        account_number = row['account_number']
        for value, limit, label in ((name, 255, 'name'), (row['phone'], 15, 'phone'),
                                    (row['account_name'], 255, 'account_name'), (row['bank'], 255, 'bank'),
                                    (account_number, 20, 'account_number')):
            if len(value) > limit:
                raise RowError(f"{label} is longer than {limit} characters.")
        email = row.get('email') or None
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise RowError(f"'{email}' is not a valid email address.")

        if account_number in seen_accounts:
            raise RowError(f"account_number {account_number} appears more than once in the file.")
        seen_accounts.add(account_number)

        existing = Vendor.objects.filter(account_number=account_number).first()
        if existing is not None:
            if existing.name.strip().lower() == name.lower():
                return 'skipped', f"vendor '{existing.name}' already exists"
            raise RowError(f"account_number {account_number} is already used by vendor '{existing.name}'.")

        Vendor.objects.create(
            owner=owner, name=name, type=vendor_type, phone=row['phone'], email=email,
            account_name=row['account_name'], bank=row['bank'], account_number=account_number,
            currency=currency, status=status,
        )
        return 'created', f"add vendor '{name}' ({row['bank']} {account_number})"

    return run_import(rows, handle_row, dry_run)
