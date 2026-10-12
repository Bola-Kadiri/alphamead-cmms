"""
Super Admin bulk upload of categories and subcategories (e.g. bill types for
Raise Payment: PHCN/Power Payment → EKEDC, IKEDC…; Waste Management → LAWMA…).

One row per subcategory:
    category, category_code, category_type, is_known_cost,
    subcategory, subcategory_code, subcategory_type, active

Only adds. Existing categories are matched by code and never renamed; the only
change ever made to one is ticking "Is known cost" (never unticking), and that
is refused if the category is already used by assets, work requests, work
orders or PPMs — ticking it would let repairs skip the WR → WO → WCC → PR chain.
"""
from utils.csv_import import RowError, parse_bool, read_csv_rows, run_import

from .models import Asset, AssetCategory, AssetSubCategory

REQUIRED_COLUMNS = ['category', 'category_code', 'subcategory', 'subcategory_code']
TEMPLATE_HEADER = [
    'category', 'category_code', 'category_type', 'is_known_cost',
    'subcategory', 'subcategory_code', 'subcategory_type', 'active',
]
TEMPLATE_ROWS = [
    ['PHCN/Power Payment', 'PHCN', 'Expense', 'yes', 'EKEDC', 'EKEDC', 'Expense', 'yes'],
    ['PHCN/Power Payment', 'PHCN', 'Expense', 'yes', 'IKEDC', 'IKEDC', 'Expense', 'yes'],
    ['Waste Management', 'WM', 'Expense', 'yes', 'LAWMA', 'LAWMA', 'Expense', 'yes'],
]


def _check_length(value, limit, label):
    if len(value) > limit:
        raise RowError(f"{label} is longer than {limit} characters.")


def _usage(category):
    from work.models import PPM, WorkOrder, WorkRequest
    usage = {
        'assets': Asset.objects.filter(category=category).count(),
        'work requests': WorkRequest.objects.filter(category=category).count(),
        'work orders': WorkOrder.objects.filter(category=category).count(),
        'PPMs': PPM.objects.filter(category=category).count(),
    }
    return ', '.join(f'{n} {label}' for label, n in usage.items() if n)


def import_categories_from_csv(file_obj, owner=None, dry_run=True):
    rows = read_csv_rows(file_obj, REQUIRED_COLUMNS)
    seen_subcategory_codes = set()

    def handle_row(row_number, row):
        category_name = row.get('category', '')
        category_code = row.get('category_code', '')
        subcategory_name = row.get('subcategory', '')
        subcategory_code = row.get('subcategory_code', '')
        if not category_code or not subcategory_name or not subcategory_code:
            raise RowError("category_code, subcategory and subcategory_code are required.")
        _check_length(category_code, 50, 'category_code')
        _check_length(category_name, 100, 'category')
        _check_length(subcategory_code, 50, 'subcategory_code')
        _check_length(subcategory_name, 100, 'subcategory')

        known_cost = parse_bool(row.get('is_known_cost'), default=False)
        active = parse_bool(row.get('active'), default=True)
        category_type = row.get('category_type') or 'Expense'
        _check_length(category_type, 50, 'category_type')

        if subcategory_code.lower() in seen_subcategory_codes:
            raise RowError(f"subcategory_code '{subcategory_code}' appears more than once in the file.")
        seen_subcategory_codes.add(subcategory_code.lower())

        notes = []
        category = AssetCategory.objects.filter(code__iexact=category_code).first()
        if category is None:
            if not category_name:
                raise RowError(f"Category '{category_code}' doesn't exist yet, so its name is required.")
            category = AssetCategory.objects.create(
                owner=owner, code=category_code, name=category_name,
                type=category_type, is_known_cost=known_cost,
            )
            notes.append(f"new category '{category.name}'" + (' (known-cost)' if known_cost else ''))
        else:
            if category_name and category_name.lower() != category.name.lower():
                notes.append(f"category kept as '{category.name}'")
            if known_cost and not category.is_known_cost:
                used = _usage(category)
                if used:
                    raise RowError(
                        f"'{category.name}' can't be marked known-cost: it is already used by {used}. "
                        "Use a separate bills-only category."
                    )
                category.is_known_cost = True
                category.save(update_fields=['is_known_cost'])
                notes.append(f"'{category.name}' marked known-cost")

        existing = AssetSubCategory.objects.filter(code__iexact=subcategory_code).select_related('asset_category').first()
        if existing is not None:
            if existing.asset_category_id != category.pk:
                raise RowError(
                    f"subcategory_code '{subcategory_code}' is already used under '{existing.asset_category.name}'."
                )
            notes.append(f"subcategory '{existing.name}' already exists")
            status = 'updated' if any('known-cost' in n or 'new category' in n for n in notes) else 'skipped'
            return status, '; '.join(notes)

        subcategory_type = row.get('subcategory_type') or category.type or 'Expense'
        _check_length(subcategory_type, 50, 'subcategory_type')
        AssetSubCategory.objects.create(
            owner=owner, code=subcategory_code, name=subcategory_name, type=subcategory_type,
            asset_category=category, is_active=active,
        )
        notes.insert(0, f"add '{subcategory_name}' under '{category.name}'")
        return 'created', '; '.join(notes)

    return run_import(rows, handle_row, dry_run)
