from django.core.management.base import BaseCommand
from reservations.models import Restaurant
from reservations.utils import generate_restaurant_speech_file

class Command(BaseCommand):
    help = 'Convert restaurant information to text-to-speech'

    def handle(self, *args, **kwargs):
        # Fetch all restaurant instances
        restaurants = Restaurant.objects.all()

        for restaurant in restaurants:
            # Generate the TTS file for the restaurant
            file_path = generate_restaurant_speech_file(restaurant)
            self.stdout.write(self.style.SUCCESS(f"Audio file saved at: {file_path}"))
