"""
Bulk import of sites (Facilities), zones, spaces (Subsystems) and assets
from a CSV export such as the WBG site asset registers.

Expected header:
    site_code, zone_code, subzone_name, location, system_name,
    component_name, description, asset_tag, qr_code, asset_status

`location` is stored on the Asset itself (not the subzone), since a single
subzone name can legitimately carry different location text per asset row.

Re-running the import is safe: assets are matched/updated by asset_tag,
and sites/zones/spaces/categories are looked up before being created.
"""
import csv
import io

from django.db import transaction
from django.utils.text import slugify

from facility.models import Facility, Zone, Subsystem
from .models import Asset
from .models.assets_category import AssetCategory, AssetSubCategory

REQUIRED_COLUMNS = {
    'site_code', 'zone_code', 'subzone_name', 'system_name',
    'component_name', 'description', 'asset_tag',
}

CSV_FIELDNAMES = [
    'site_code', 'zone_code', 'subzone_name', 'location', 'system_name',
    'component_name', 'description', 'asset_tag', 'qr_code', 'asset_status',
]

ASSET_STATUS_CHOICES = {choice for choice, _label in Asset._meta.get_field('status').choices}


def _code_from(text, max_length=45):
    code = slugify(text).upper().replace('-', '_')[:max_length]
    return code or 'UNSPECIFIED'


def _unique_code(model, text, exclude_name):
    """Slugify `text` into a code for `model`, disambiguating collisions
    against an unrelated existing row (same code, different name)."""
    base = _code_from(text)
    code = base
    suffix = 2
    while model.objects.filter(code=code).exclude(name=exclude_name).exists():
        code = f"{base}_{suffix}"
        suffix += 1
    return code


def _normalize_row(header, raw_row):
    """
    Some source exports (e.g. WBG_Assets_Benin_Cotonou.csv) contain an
    un-quoted comma inside the free-text 'description' column (e.g.
    "Water Tank with Connection 30,000 Litres - Qty: 1"), which splits
    that single field into two columns and shifts everything after it.
    Detect the shift and fold the extra column(s) back into 'description'.
    """
    if len(raw_row) == len(header):
        return dict(zip(header, raw_row))
    if len(raw_row) < len(header):
        raise ValueError(f"Row has fewer columns ({len(raw_row)}) than the header ({len(header)}).")

    desc_idx = header.index('description')
    extra = len(raw_row) - len(header)
    merged_description = ','.join(raw_row[desc_idx: desc_idx + extra + 1])
    fixed_row = raw_row[:desc_idx] + [merged_description] + raw_row[desc_idx + extra + 1:]
    return dict(zip(header, fixed_row))


def import_assets_from_csv(file_obj, owner=None):
    """
    file_obj: a file-like object opened in text mode (or binary — both are
    accepted) positioned at the start of the CSV.
    owner: the user to record as `owner` on newly created rows (optional).

    Returns a summary dict of what was created/updated.
    """
    if hasattr(file_obj, 'read'):
        raw = file_obj.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        text_stream = io.StringIO(raw)
    else:
        text_stream = file_obj

    reader = csv.reader(text_stream)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("CSV file is empty.")

    missing = REQUIRED_COLUMNS - set(header)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    facilities, zones, subsystems = {}, {}, {}
    categories, subcategories = {}, {}

    summary = {
        'facilities_created': 0,
        'zones_created': 0,
        'subsystems_created': 0,
        'subsystems_updated': 0,
        'assets_created': 0,
        'assets_updated': 0,
        'rows_processed': 0,
    }

    with transaction.atomic():
        for row_num, raw_row in enumerate(reader, start=2):
            if not raw_row or not any(raw_row):
                continue
            row = _normalize_row(header, raw_row)

            site_code = (row.get('site_code') or '').strip()
            zone_code = (row.get('zone_code') or '').strip()
            subzone_name = (row.get('subzone_name') or '').strip()
            location = (row.get('location') or '').strip()
            system_name = (row.get('system_name') or '').strip()
            component_name = (row.get('component_name') or '').strip()
            description = (row.get('description') or '').strip()
            asset_tag = (row.get('asset_tag') or '').strip()
            qr_code = (row.get('qr_code') or '').strip() or None
            asset_status = (row.get('asset_status') or '').strip().upper() or 'IN_SERVICE'

            if not site_code or not asset_tag:
                raise ValueError(f"Row {row_num}: 'site_code' and 'asset_tag' are required.")
            if not zone_code or not subzone_name or not system_name or not component_name:
                raise ValueError(
                    f"Row {row_num}: 'zone_code', 'subzone_name', 'system_name' and "
                    "'component_name' are all required (Asset now requires a full "
                    "facility/zone/subzone/category/component chain)."
                )
            if asset_status not in ASSET_STATUS_CHOICES:
                asset_status = 'IN_SERVICE'

            facility = facilities.get(site_code)
            if facility is None:
                facility, was_created = Facility.objects.get_or_create(
                    code=site_code,
                    defaults={'name': site_code, 'owner': owner},
                )
                if was_created:
                    summary['facilities_created'] += 1
                facilities[site_code] = facility

            zone = None
            if zone_code:
                zone_key = (facility.pk, zone_code)
                zone = zones.get(zone_key)
                if zone is None:
                    zone, was_created = Zone.objects.get_or_create(
                        code=f"{site_code}-{zone_code}",
                        defaults={'name': zone_code, 'facility': facility, 'owner': owner},
                    )
                    if was_created:
                        summary['zones_created'] += 1
                    zones[zone_key] = zone

            subsystem = None
            if subzone_name:
                sub_key = (facility.pk, subzone_name)
                subsystem = subsystems.get(sub_key)
                if subsystem is None:
                    sub_defaults = {'owner': owner}
                    if zone is not None:
                        sub_defaults['zone'] = zone
                    subsystem, was_created = Subsystem.objects.update_or_create(
                        facility=facility,
                        name=subzone_name,
                        defaults=sub_defaults,
                    )
                    if was_created:
                        summary['subsystems_created'] += 1
                    else:
                        summary['subsystems_updated'] += 1
                    subsystems[sub_key] = subsystem

            category = None
            if system_name:
                category = categories.get(system_name)
                if category is None:
                    category, _created = AssetCategory.objects.get_or_create(
                        name=system_name,
                        defaults={'type': 'System', 'code': _unique_code(AssetCategory, system_name, system_name)},
                    )
                    categories[system_name] = category

            subcategory = None
            if component_name and category is not None:
                subcat_key = (category.pk, component_name)
                subcategory = subcategories.get(subcat_key)
                if subcategory is None:
                    subcategory, _created = AssetSubCategory.objects.get_or_create(
                        asset_category=category,
                        name=component_name,
                        defaults={
                            'type': 'Component',
                            'code': _unique_code(AssetSubCategory, f"{system_name}-{component_name}", component_name),
                        },
                    )
                    subcategories[subcat_key] = subcategory

            asset, was_created = Asset.objects.update_or_create(
                asset_tag=asset_tag,
                defaults={
                    'facility': facility,
                    'zone': zone,
                    'subsystem': subsystem,
                    'category': category,
                    'subcategory': subcategory,
                    'asset_name': description or component_name or asset_tag,
                    'location': location or None,
                    'qr_code': qr_code,
                    'status': asset_status,
                    'owner': owner,
                },
            )
            summary['assets_created' if was_created else 'assets_updated'] += 1
            summary['rows_processed'] += 1

    return summary


def asset_to_row(asset):
    """Map a single Asset back to a dict in the WBG CSV template shape."""
    zone = asset.zone or (asset.subsystem.zone if asset.subsystem else None)
    return {
        'site_code': asset.facility.code if asset.facility else '',
        'zone_code': zone.name if zone else '',
        'subzone_name': asset.subsystem.name if asset.subsystem else '',
        'location': asset.location or (asset.subsystem.name if asset.subsystem else ''),
        'system_name': asset.category.name if asset.category else '',
        'component_name': asset.subcategory.name if asset.subcategory else '',
        'description': asset.asset_name,
        'asset_tag': asset.asset_tag,
        'qr_code': asset.qr_code or '',
        'asset_status': asset.status,
    }


def export_assets_to_csv(queryset, file_obj):
    """Write `queryset` (an Asset queryset) to `file_obj` in the WBG CSV template shape."""
    queryset = queryset.select_related(
        'facility', 'zone', 'subsystem', 'subsystem__zone', 'category', 'subcategory',
    )
    writer = csv.DictWriter(file_obj, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for asset in queryset:
        writer.writerow(asset_to_row(asset))


def format_import_summary(summary):
    return (
        f"{summary['rows_processed']} rows processed, "
        f"{summary['facilities_created']} sites created, "
        f"{summary['zones_created']} zones created, "
        f"{summary['subsystems_created']} spaces created, "
        f"{summary['subsystems_updated']} spaces updated, "
        f"{summary['assets_created']} assets created, "
        f"{summary['assets_updated']} assets updated."
    )
