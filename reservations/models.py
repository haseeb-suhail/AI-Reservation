from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.core.validators import EmailValidator, RegexValidator, URLValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User


class RestaurantManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class Restaurant(AbstractBaseUser):
    restaurant_name = models.CharField(max_length=255, null=True, blank=True)
    restaurant_address = models.CharField(max_length=255, null=True, blank=True)
    restaurant_contact_number = models.CharField(max_length=255, null=True, blank=True)
    restaurant_information = models.TextField(null=True, blank=True)
    available_tables = models.IntegerField(verbose_name=_('Available Tables'), null=True, blank=True)
    opening_hours = models.CharField(verbose_name=_('Opening Hours'), null=True, blank=True)
    closing_hours = models.CharField(verbose_name=_('Closing Hours'), null=True, blank=True)
    cuisines = models.TextField(null=True, blank=True)
    website = models.URLField(validators=[URLValidator()], blank=True, null=True)
    social_media_links = models.JSONField(null=True, blank=True, verbose_name=_('Social Media Links'))
    seating_capacity = models.IntegerField(verbose_name=_('Seating Capacity'), null=True, blank=True)
    unique_url = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=True, blank=True)
    public_profile_url = models.URLField(max_length=500, blank=True, null=True)  # Store the full URL
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)  # Add unique constraint here
    email = models.EmailField(unique=True, null=True, blank=True)  # Add unique constraint here

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'

    objects = RestaurantManager()

    def save(self, *args, **kwargs):
        if not self.public_profile_url:
            base_url = 'http://localhost:8000/api'
            path = f'/restaurants/{self.unique_url}/profile/'
            self.public_profile_url = f'{base_url}{path}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.restaurant_name

    def clean(self):
        """Custom validation to ensure opening hours are before closing hours."""
        if self.opening_hours >= self.closing_hours:
            raise ValidationError(_("Opening hours must be before closing hours."))


class Reservation(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reservations')
    name = models.CharField(max_length=255)
    user_email = models.EmailField(validators=[EmailValidator()])
    contact_user = models.CharField(max_length=20)
    booking_info = models.TextField(null=True , blank=True)
    reservation_time = models.CharField(null=True, blank=True, verbose_name="Reservation Time")
    special_requests = models.TextField(null=True, blank=True, verbose_name="Special Requests")
    speech_to_text_notes = models.TextField(null=True, blank=True, verbose_name="Speech-to-Text Notes")

    def __str__(self):
        return f"{self.name} - {self.restaurant.restaurant_name}"

    # def clean(self):
    #     """Custom validation to ensure reservation time is within restaurant's hours."""
    #     if not (self.restaurant.opening_hours <= self.reservation_time.time() <= self.restaurant.closing_hours):
    #         raise ValidationError(_("Reservation time must be within the restaurant's operating hours."))


class Notification(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='notifications')
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.restaurant.restaurant_name} - Reservation by {self.reservation.name}"

