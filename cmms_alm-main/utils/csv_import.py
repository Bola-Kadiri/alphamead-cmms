"""
Shared helpers for the Super Admin bulk uploads (bill categories/subcategories
and vendors).

Unlike the asset import, which stops at the first bad row, these check every
row and report all problems at once — but save nothing unless the whole file
is clean (all-or-nothing). A preview (dry run) runs the exact same steps and
rolls them back.
"""
import csv
import io

from django.db import transaction
from django.http import HttpResponse

TRUE_VALUES = {'yes', 'y', 'true', '1'}
FALSE_VALUES = {'no', 'n', 'false', '0'}


class RowError(Exception):
    """A problem with one CSV row — reported, and blocks saving the file."""


def read_csv_rows(file_obj, required_columns):
    """Return a list of (row_number, {column: value}) with lower-cased, stripped headers."""
    raw = file_obj.read()
    if isinstance(raw, bytes):
        try:
            raw = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError("The file must be a CSV saved as UTF-8 (in Excel: Save As → CSV UTF-8).")
    reader = csv.reader(io.StringIO(raw))
    try:
        # "Account number" and "account_number" are the same column.
        header = ['_'.join(h.strip().lower().split()) for h in next(reader)]
    except StopIteration:
        raise ValueError("The CSV file is empty.")

    missing = [c for c in required_columns if c not in header]
    if missing:
        raise ValueError(f"The CSV is missing these columns: {', '.join(missing)}. Download the template.")

    rows = []
    for row_number, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        rows.append((row_number, {
            column: (values[i].strip() if i < len(values) else '')
            for i, column in enumerate(header)
        }))
    if not rows:
        raise ValueError("The CSV has a header but no rows.")
    return rows


def parse_bool(value, default):
    value = (value or '').strip().lower()
    if not value:
        return default
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise RowError(f"'{value}' is not a yes/no value.")


def run_import(rows, handle_row, dry_run):
    """
    Run `handle_row(row_number, row)` for every row inside one transaction.
    handle_row returns (status, message) — e.g. ('created', "…") — or raises
    RowError. Everything is rolled back on a dry run or if any row failed.
    """
    results = []
    with transaction.atomic():
        for row_number, row in rows:
            try:
                status, message = handle_row(row_number, row)
            except RowError as exc:
                status, message = 'error', str(exc)
            results.append({'row': row_number, 'status': status, 'message': message})

        errors = sum(1 for r in results if r['status'] == 'error')
        if dry_run or errors:
            transaction.set_rollback(True)

    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    return {
        'dry_run': dry_run,
        'saved': not dry_run and errors == 0,
        'errors': errors,
        'counts': counts,
        'rows': results,
    }


def csv_template_response(filename, header, sample_rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(sample_rows)
    return response


def is_super_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, 'roles', None) == 'SUPER ADMIN'))
