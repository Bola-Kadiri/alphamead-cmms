import uuid
import random
import string


from django.db import models
from django.db.models import Count
from django.db.models.deletion import CASCADE, SET_NULL
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _





class UserManager(BaseUserManager):
    def create_user(self, email, password, first_name, last_name, is_active=False, is_staff=False, is_admin=False, is_superuser=False):
        "Create and saves a User with the given email and password"
        if not email:
            raise ValueError(_('Users must have an email address'))
        if not password:
            raise ValueError(_('Users must have a password'))

        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.username = self.normalize_email(email)
        user.is_active = True
        user.save(using=self._db)
        print("create user method was used")
        return user

    def create_superuser(self, email, first_name, last_name, password=None):
        "Creates and saves a superuser with the given email and password"
        user = self.create_user(
            email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
        user.is_superuser = True
        user.is_staff = True
        user.is_admin = True
        user.is_active = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    # ROLES_TYPE_CHOICES = [
    #     ('Super Admin', _('Super Admin')),
    #     ('Facility Admin', _('Facility Admin')),
    #     ('Facility Procurement', _('Facility Procurement')),
    #     ('Facility Manager', _('Facility Manager')),
    #     ('Facility Officer', _('Facility Officer')),
    #     ('Facility Auditor', _('Facility Auditor')),
    #     ('Facility Account', _('Facility Account')),
    #     ('Facility Store', _('Facility Store')),
    #     ('Facility View', _('Facility View')),
    # ]
    ROLES_TYPE_CHOICES = [
        ('SUPER ADMIN', _('Super Admin')),
        ('ADMIN', _('Admin')),
        ('REQUESTER', _('Requester')),
        ('REVIEWER', _('Reviewer')),
        ('APPROVER', _('Approver')),
        ('PROCUREMENT AND STORE', _('Procurement and store')),
    ]
    STATUS_CHOICES = [
        ('Active', _('Active')),
        ('Inactive', _('Inactive')),
    ]
    
    GENDER_CHOICES = [
        ('Male', _('Male')),
        ('Female', _('Female')),
        ('Other', _('Other')),
    ]
    
    def upload_location(instance, filename):
        file_path = 'patient/images/{id}/{filename}'.format(
            id=str(instance.id), filename=filename)
        return file_path

    user_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Unique ID for the user.")
    )
    
    first_name = models.CharField(
        max_length=100,
        help_text=_("First name of the user.")
    )
    
    last_name = models.CharField(
        max_length=100,
        help_text=_("Last name of the user.")
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text=_("Unique slugified identifier for the user.")
    )
    
    roles = models.CharField(
        max_length=50,
        choices=ROLES_TYPE_CHOICES,
        default='Facility View',
        help_text=_("Type of user.")
    )
    
    email = models.EmailField(
        max_length=60,
        unique=True,
        help_text=_("Email address of the user.")
    )
    
    username = models.CharField(
        max_length=60,
        unique=True,
        blank=True,
        help_text=_("Username for the user (auto-generated from email).")
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text=_("Phone number of the user.")
    )
    
    designation = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text=_("Designation of the user.")
    )
    
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='subordinates',
        help_text=_("Supervisor of the user.")
    )
    
    date_of_birth = models.DateField(
        blank=True, null=True,
        help_text=_("Date of birth of the user.")
    )
    
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True, null=True,
        help_text=_("Gender of the user.")
    )
    
    nationality = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Nationality of the user.")
    )
    
    passport_number = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text=_("Passport number of the user.")
    )
    
    address = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_("Address of the user.")
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='Active',
        help_text=_("Status of the user.")
    )
    
    avatar = models.ImageField(
        default='avatar.png', 
        upload_to=upload_location, 
        blank=True, 
        null=True,
        help_text=_('Profile of the user')
    )
    
    # privileges section
    
    team_lead = models.BooleanField(
      default=False
    )
    
    generate_reports = models.BooleanField(
      default=False
    )
    
    approval_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True,
        help_text=_("Approval limit for the user.")
    )
    
    
    date_joined = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Date and time the user joined.")
    )
    
    last_login = models.DateTimeField(
        auto_now=True,
        help_text=_("Last login date and time.")
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user is verified.")
    )
    
    is_blocked = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user is blocked.")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Indicates if the user account is active.")
    )
    
    is_staff = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user is a staff member.")
    )
    
    is_admin = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user is an admin.")
    )
    
    is_superuser = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user is a superuser.")
    )
    
    
    # permissions section
    access_to_all_facilities = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all facilities.")
    )
    
    facility = models.ManyToManyField(
        'facility.Facility',
        blank=True,
        help_text=_("Facilities the user is assigned to."),
        related_name='users_facilities'
    )
    
    access_to_all_buildings = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all buildings.")
    ) 
    
    buildings = models.ManyToManyField(
        'facility.Building',
        blank=True,
        help_text=_("Buildings the user is assigned to."),
        related_name='users_buildings'
    )
    
    access_to_all_apartments = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all apartments.")
    )
    
    apartments = models.ManyToManyField(
        'facility.Apartment',
        blank=True,
        related_name='users_apartments',
        help_text=_("Apartments the user is assigned to.")
    )
    
    
    
    access_to_all_categories = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all assets categories.")
    )
    
    categories = models.ManyToManyField(
        'accounts.Category',
        blank=True,
        related_name='users_categories',
        help_text=_("Asset categories the user is assigned to.")
    )
    
    access_to_all_warehouses = models.BooleanField(
        default=False,  
        help_text=_("Indicates if the user has access to all warehouses.")
    )
    
    warehouse = models.ManyToManyField(
        'asset_inventory.Warehouse',
        blank=True,
        related_name='users_warehouses',
        help_text=_("Warehouses the user is assigned to.")
    )
    
    
    access_to_all_clients = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all clients.")
    )
    
    clients = models.ManyToManyField(
        'accounts.Client',
        blank=True,
        related_name='users_clients',
        help_text=_("Clients the user is assigned to.")
    )
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            return '/media/avatar.png'
    
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  # email & Password are required by default.
    READONLY_FIELDS = ['date_joined', 'last_login']

    objects = UserManager()

    def __str__(self):
        return str(self.email)

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def isSuperUser(self):
        "Is the user a super user?"
        return self.is_superuser
    
    class Meta:
        ordering = ['-id']
    
    
    def save(self, *args, **kwargs):
        # Set username from email if not provided
        if not self.username:
            self.username = self.email
            
        # Generate a unique slug before saving
        if not self.slug:
            base_slug = slugify(self.name)  # Use the name property to generate the slug
            slug = base_slug
            counter = 0
            while User.objects.filter(slug=slug).exists():
                # Append random characters to make the slug unique
                counter += 1
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                slug = f"{base_slug}-{random_suffix}"

            self.slug = slug

        super().save(*args, **kwargs)