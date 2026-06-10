"""
Management command to sync reference data from production to local DB.

Usage:
    python manage.py sync_from_prod --email <admin@example.com> --password <secret>

Optional:
    --prod-url https://alpha-cmms.alphamead.com   (default)
"""
import requests
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from asset_inventory.models import AssetCategory, AssetSubCategory, Asset
from facility.models import Region, Cluster, Facility, Zone, Building
from accounts.models import Department, Vendor

User = get_user_model()
DEFAULT_PROD_URL = "https://api-cmms.alphamead.com"


class Command(BaseCommand):
    help = "Sync reference data (categories, facilities, assets, departments) from production"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Production admin email")
        parser.add_argument("--password", required=True, help="Production admin password")
        parser.add_argument("--prod-url", default=DEFAULT_PROD_URL, help="Production base URL")

    def handle(self, *args, **options):
        base = options["prod_url"].rstrip("/")
        self.stdout.write(f"Connecting to {base} ...")

        token = self._get_token(base, options["email"], options["password"])
        self.headers = {"Authorization": f"Bearer {token}"}
        self.base = base

        # owner for newly created local records
        self.owner = User.objects.filter(is_superuser=True).first() or User.objects.first()

        # ID maps: prod_id -> local Django object
        self.facility_map = {}
        self.building_map = {}
        self.category_map = {}
        self.subcategory_map = {}

        self._sync_asset_categories()
        self._sync_asset_subcategories()
        self._sync_regions()
        self._sync_clusters()
        self._sync_facilities()
        self._sync_buildings()
        self._sync_departments()
        self._sync_vendors()
        self._sync_assets()

        self.stdout.write(self.style.SUCCESS("\nSync complete!"))
        self.stdout.write(f"  AssetCategories   : {AssetCategory.objects.count()}")
        self.stdout.write(f"  AssetSubCategories: {AssetSubCategory.objects.count()}")
        self.stdout.write(f"  Regions           : {Region.objects.count()}")
        self.stdout.write(f"  Clusters          : {Cluster.objects.count()}")
        self.stdout.write(f"  Facilities        : {Facility.objects.count()}")
        self.stdout.write(f"  Buildings         : {Building.objects.count()}")
        self.stdout.write(f"  Departments       : {Department.objects.count()}")
        self.stdout.write(f"  Vendors           : {Vendor.objects.count()}")
        self.stdout.write(f"  Assets            : {Asset.objects.count()}")

    # ------------------------------------------------------------------ helpers

    def _get_token(self, base, email, password):
        resp = requests.post(
            f"{base}/auth/token/",
            json={"email": email, "password": password},
            timeout=30,
        )
        if resp.status_code != 200:
            raise CommandError(
                f"Authentication failed ({resp.status_code}): {resp.text}"
            )
        data = resp.json()
        return data.get("access") or data.get("token")

    def _paginate(self, path):
        """Yield all items, following DRF pagination."""
        url = f"{self.base}{path}"
        while url:
            resp = requests.get(url, headers=self.headers, timeout=30)
            if resp.status_code == 404:
                self.stderr.write(f"  WARNING: {path} not found (404) — skipping")
                return
            if resp.status_code != 200:
                self.stderr.write(
                    f"  WARNING: {path} returned {resp.status_code} — skipping"
                )
                return
            data = resp.json()
            if isinstance(data, list):
                yield from data
                return
            yield from data.get("results", [])
            url = data.get("next")

    # ------------------------------------------------------------------ sync

    def _sync_asset_categories(self):
        self.stdout.write("Syncing asset categories ...")
        created = updated = 0
        for item in self._paginate("/asset_inventory/api/asset-categories/"):
            obj, was_created = AssetCategory.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "description": item.get("description") or "",
                    "salvage_value_percent": item.get("salvage_value_percent"),
                    "useful_life_year": item.get("useful_life_year"),
                    "owner": self.owner,
                },
            )
            self.category_map[item["id"]] = obj
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_asset_subcategories(self):
        self.stdout.write("Syncing asset subcategories ...")
        created = updated = skipped = 0
        for item in self._paginate("/asset_inventory/api/asset-subcategories/"):
            # asset_category_detail.code is returned by AssetSubCategorySerializer
            detail = item.get("asset_category_detail") or {}
            cat_code = detail.get("code")
            category = AssetCategory.objects.filter(code=cat_code).first() if cat_code else None
            if not category:
                # fallback via ID map (prod id)
                prod_cat_id = item.get("asset_category")
                category = self.category_map.get(prod_cat_id)
            if not category:
                skipped += 1
                continue
            obj, was_created = AssetSubCategory.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "description": item.get("description") or "",
                    "asset_category": category,
                    "is_active": item.get("is_active", True),
                    "owner": self.owner,
                },
            )
            self.subcategory_map[item["id"]] = obj
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            f"  created={created}  updated={updated}  skipped(no category)={skipped}"
        )

    def _sync_regions(self):
        self.stdout.write("Syncing regions ...")
        created = updated = 0
        for item in self._paginate("/facility/api/api/regions/"):
            obj, was_created = Region.objects.update_or_create(
                name=item["name"],
                defaults={
                    "country": item.get("country", ""),
                    "owner": self.owner,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_clusters(self):
        self.stdout.write("Syncing clusters ...")
        created = updated = 0
        for item in self._paginate("/facility/api/api/clusters/"):
            # ClusterSerializer returns region_detail with {id, name, country}
            region_name = (item.get("region_detail") or {}).get("name")
            region = Region.objects.filter(name=region_name).first() if region_name else None
            obj, was_created = Cluster.objects.update_or_create(
                name=item["name"],
                defaults={
                    "region": region,
                    "owner": self.owner,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_facilities(self):
        self.stdout.write("Syncing facilities ...")
        created = updated = 0
        for item in self._paginate("/facility/api/api/facilities/"):
            # FacilitySerializer returns cluster_detail with {id, name, region}
            cluster_name = (item.get("cluster_detail") or {}).get("name")
            cluster = Cluster.objects.filter(name=cluster_name).first() if cluster_name else None
            obj, was_created = Facility.objects.update_or_create(
                name=item["name"],
                defaults={
                    "cluster": cluster,
                    "code": item.get("code", ""),
                    "type": item.get("type", ""),
                    "address_gps": item.get("address_gps", ""),
                    "owner": self.owner,
                },
            )
            self.facility_map[item["id"]] = obj
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_buildings(self):
        self.stdout.write("Syncing buildings ...")
        created = updated = 0
        for item in self._paginate("/facility/api/api/buildings/"):
            # BuildingSerializer returns facility_detail with {id, code, name, cluster}
            facility_name = (item.get("facility_detail") or {}).get("name")
            facility = Facility.objects.filter(name=facility_name).first() if facility_name else None
            if not facility:
                prod_fac_id = item.get("facility")
                facility = self.facility_map.get(prod_fac_id)
            obj, was_created = Building.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item.get("name", ""),
                    "facility": facility,
                    "owner": self.owner,
                },
            )
            self.building_map[item["id"]] = obj
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_departments(self):
        self.stdout.write("Syncing departments ...")
        created = updated = 0
        # accounts endpoint returns {id, code, name, email, phone, status}
        for item in self._paginate("/accounts/api/departments/"):
            code = item.get("code", "").strip()
            if not code:
                continue
            obj, was_created = Department.objects.update_or_create(
                code=code,
                defaults={
                    "name": item.get("name", ""),
                    "email": item.get("email", "") or f"dept-{code}@local.invalid",
                    "phone": item.get("phone", ""),
                    "owner": self.owner,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_vendors(self):
        self.stdout.write("Syncing vendors ...")
        created = updated = 0
        for item in self._paginate("/accounts/api/vendors/"):
            account_number = (item.get("account_number") or "").strip()
            if not account_number:
                continue
            obj, was_created = Vendor.objects.update_or_create(
                account_number=account_number,
                defaults={
                    "name": item.get("name", ""),
                    "type": item.get("type", "Company"),
                    "phone": item.get("phone", ""),
                    "email": item.get("email") or None,
                    "account_name": item.get("account_name", ""),
                    "bank": item.get("bank", ""),
                    "currency": item.get("currency", "NGN"),
                    "owner": self.owner,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"  created={created}  updated={updated}")

    def _sync_assets(self):
        self.stdout.write("Syncing assets ...")
        created = updated = skipped = 0
        for item in self._paginate("/asset_inventory/api/assets/"):
            asset_tag = (item.get("asset_tag") or "").strip()
            if not asset_tag:
                skipped += 1
                continue

            # Resolve category/subcategory via detail.code or ID map
            cat_code = (item.get("category_detail") or {}).get("code")
            category = (
                AssetCategory.objects.filter(code=cat_code).first()
                if cat_code
                else self.category_map.get(item.get("category"))
            )

            subcat_code = (item.get("subcategory_detail") or {}).get("code")
            subcategory = (
                AssetSubCategory.objects.filter(code=subcat_code).first()
                if subcat_code
                else self.subcategory_map.get(item.get("subcategory"))
            )

            # Resolve facility and building via ID map built during earlier sync
            facility = self.facility_map.get(item.get("facility"))
            building = self.building_map.get(item.get("building"))

            obj, was_created = Asset.objects.update_or_create(
                asset_tag=asset_tag,
                defaults={
                    "asset_name": item.get("asset_name", ""),
                    "asset_type": item.get("asset_type", "Asset"),
                    "condition": item.get("condition"),
                    "purchase_date": item.get("purchase_date"),
                    "purchased_amount": item.get("purchased_amount"),
                    "serial_number": item.get("serial_number") or None,
                    "lifespan": item.get("lifespan") or "",
                    "facility": facility,
                    "building": building,
                    "category": category,
                    "subcategory": subcategory,
                    "owner": self.owner,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            f"  created={created}  updated={updated}  skipped(no tag)={skipped}"
        )
