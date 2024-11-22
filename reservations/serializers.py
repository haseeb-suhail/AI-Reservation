from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Reservation, Restaurant, Notification



Restaurant_user = get_user_model()


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id',
            'username',
            'email',
            'restaurant_name',
            'restaurant_address',
            'restaurant_contact_number',
            'password',
            'confirm_password',
        ]

    def validate(self, data):
        # Ensure password and confirm_password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        # Remove confirm_password since we don't need it for object creation
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')

        # Create the restaurant object
        restaurant = Restaurant.objects.create(**validated_data)
        restaurant.set_password(password)  # Hash the password
        restaurant.save()

        return restaurant







class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)  # Accepts both username and email
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Restaurant
        fields = ['username', 'password']


    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise serializers.ValidationError('Both username and password are required.')

        # Authenticate using the custom backend
        user = authenticate(request=self.context.get('request'), username=username, password=password)

        if not user:
            raise serializers.ValidationError('Invalid credentials.')

        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField()  # Change to CharField for username

    def validate(self, data):
        email = data.get('email')
        if not Restaurant.objects.filter(email=email).exists():
            raise serializers.ValidationError("User does not exist.")
        return data


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            'id',
            'restaurant',
            'name',
            'user_email',
            'contact_user',
            'booking_info',
            'reservation_time',
            'special_requests',
            'speech_to_text_notes',
        ]
        # read_only_fields = ['restaurant']
        #
        # def create(self, validated_data):
        #     restaurant = self.context['restaurant']
        #     validated_data['restaurant'] = restaurant
        #     return super().create(validated_data)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make only specific fields required
        self.fields['name'].required = True
        self.fields['user_email'].required = True
        self.fields['contact_user'].required = True

        # Make other fields optional
        self.fields['restaurant'].required = False
        self.fields['booking_info'].required = False
        self.fields['reservation_time'].required = False
        self.fields['special_requests'].required = False
        self.fields['speech_to_text_notes'].required = False
    # def validate(self, data):
    #     """Custom validation for reservation time."""
    #     restaurant = data.get('restaurant')
    #     reservation_time = data.get('reservation_time')
    #
    #     if reservation_time is None:
    #         raise serializers.ValidationError("Reservation time cannot be None.")
    #
    #     if restaurant:
    #         opening_hours = restaurant.opening_hours
    #         closing_hours = restaurant.closing_hours
    #
    #         if opening_hours is None or closing_hours is None:
    #             raise serializers.ValidationError("Restaurant's operating hours must be set.")
    #
    #         # Perform time comparisons
    #         if not (opening_hours <= reservation_time <= closing_hours):
    #             raise serializers.ValidationError("Reservation time must be within the restaurant's operating hours.")
    #
    #     return data


class NotificationSerializer(serializers.ModelSerializer):
    formatted_message = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['created_at', 'is_read', 'formatted_message']
        read_only_fields = ['created_at']

    def get_formatted_message(self, obj):
        # Fetch related reservation and restaurant data
        reservation = obj.reservation
        restaurant = obj.restaurant

        # Construct the formatted message
        message = (
            f"{reservation.name} has made a reservation at restaurant: {restaurant.restaurant_name}, "
            f"location: {restaurant.restaurant_address}. "
            f"Reservation Details: User Email: {reservation.user_email}, "
            f"Contact User: {reservation.contact_user}, Booking Info: {reservation.booking_info}, "
            f"Reservation Time: {reservation.reservation_time}, "
            f"Special Requests: {reservation.special_requests}, "
            # f"Speech-to-Text Notes: {reservation.speech_to_text_notes}."
        )
        return message


class RestaurantProfileSerializer(serializers.ModelSerializer):
    notifications = NotificationSerializer(many=True, read_only=True)
    class Meta:
        model = Restaurant
        fields = [
            'id',
            'username',
            'email',
            'restaurant_name',
            'restaurant_address',
            'restaurant_contact_number',
            'restaurant_information',  # Additional fields for profile
            'available_tables',
            'opening_hours',
            'closing_hours',
            'cuisines',
            'website',
            'social_media_links',
            'seating_capacity',
            'unique_url',
            'public_profile_url',
            'notifications',
        ]

    def to_representation(self, instance):
        # Get the standard representation
        representation = super().to_representation(instance)

        # Hide URLs if necessary
        if self.context.get('hide_urls', False):
            representation.pop('unique_url', None)
            representation.pop('public_profile_url', None)

        return representation


