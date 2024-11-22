import os
from django.conf import settings
from django.http import HttpResponse, Http404, FileResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import ReservationSerializer, NotificationSerializer, SignUpSerializer, RestaurantProfileSerializer, \
    LoginSerializer
from .models import Restaurant, Reservation, Notification
import logging
from .utils import text_to_speech_file, generate_restaurant_speech_file
import assemblyai as aai
import dateparser
import re
from datetime import datetime
from django.utils.dateparse import parse_datetime


logger = logging.getLogger(__name__)


class SignupView(APIView):
    @swagger_auto_schema(
        request_body=SignUpSerializer,
        responses={201: SignUpSerializer,
                   status.HTTP_400_BAD_REQUEST: 'Bad Request'}
    )
    def post(self, request, *args, **kwargs):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={201: LoginSerializer,
                   status.HTTP_400_BAD_REQUEST: 'Bad Request'}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            # 'username': user.username,
            # # 'profile_image': user.profile_image,
            # 'first_name': user.first_name,
            # 'last_name': user.last_name,
            # 'email': user.email,
            'refresh': str(refresh),
            'access': str(access),
        }, status=status.HTTP_200_OK)


class RestaurantProfileView(generics.RetrieveUpdateAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # context['hide_urls'] = True  # Optionally hide URLs
        return context

    def get_object(self):
        return self.request.user  # Assuming the user is authenticated

# class RestaurantProfileView(APIView):
#     queryset = Restaurant.objects.all()
#     serializer_class = RestaurantProfileSerializer
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         restaurant = request.user
#
#         if not isinstance(restaurant, Restaurant):
#             return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
#         # Fetch notifications for the restaurant
#         notifications = Notification.objects.filter(restaurant=restaurant)
#         notification_serializer = NotificationSerializer(notifications, many=True)
#         serializer = RestaurantProfileSerializer(restaurant)
#         response_data = serializer.data
#         response_data['notifications'] = notification_serializer.data
#         return Response(response_data)
#
#     @swagger_auto_schema(
#         request_body=RestaurantProfileSerializer,
#         responses={201: RestaurantProfileSerializer,
#                    status.HTTP_400_BAD_REQUEST: 'Bad Request'}
#     )
#     def post(self, request, *args, **kwargs):
#         restaurant = request.user
#
#         if not isinstance(restaurant, Restaurant):
#             return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
#
#         # Mark all unread notifications as read
#         notifications = Notification.objects.filter(restaurant=restaurant, is_read=False)
#         notifications.update(is_read=True)
#
#         # Optionally, return the updated notifications
#         notification_serializer = NotificationSerializer(notifications, many=True)
#         return Response(notification_serializer.data, status=status.HTTP_200_OK)
#
#     @swagger_auto_schema(
#         request_body=RestaurantProfileSerializer,
#         responses={201: RestaurantProfileSerializer,
#                    status.HTTP_400_BAD_REQUEST: 'Bad Request'}
#     )
#     def put(self, request):
#         restaurant = request.user
#         serializer = RestaurantProfileSerializer(restaurant, data=request.data, partial=True)
#
#         if serializer.is_valid():
#             serializer.save()
#             logger.info(f'Restaurant profile updated: {restaurant.id}')
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     def delete(self, request):
#         restaurant = request.user
#
#         if not isinstance(restaurant, Restaurant):
#             return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
#
#         restaurant.delete()
#         logger.info(f'Restaurant profile deleted: {restaurant.id}')
#         return Response(status=status.HTTP_204_NO_CONTENT)


class PublicProfileView(APIView):
    permission_classes = []  # No permissions needed to access this view

    def get(self, request, unique_url, *args, **kwargs):
        try:
            restaurant = Restaurant.objects.get(unique_url=unique_url)
            serializer = RestaurantProfileSerializer(restaurant, context={'hide_urls': True})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Restaurant.DoesNotExist:
            return Response({"detail": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=ReservationSerializer,
        responses={201: ReservationSerializer,
                   status.HTTP_400_BAD_REQUEST: 'Bad Request'}
    )
    def post(self, request, unique_url, *args, **kwargs):
        try:
            restaurant = Restaurant.objects.get(unique_url=unique_url)
            data = request.data.copy()
            data['restaurant'] = restaurant.id
            print("restaurant_fetched")# Associate reservation with the restaurant
            # Serialize the reservation data
            serializer = ReservationSerializer(data=data)

            if serializer.is_valid():
                reservation = serializer.save()
                file_path = generate_restaurant_speech_file(restaurant)
                # Save the reservation
                # Create notification
                Notification.objects.create(
                    restaurant=restaurant,
                    reservation=reservation
                )
                return Response({"reservation": serializer.data, "audio_file": file_path}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        except Restaurant.DoesNotExist:
            return Response({"detail": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)


class ServeAudioFileView(APIView):
    """
    API View to serve the audio file for a restaurant.
    """

    def get(self, request, file_name, *args, **kwargs):
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

        if os.path.exists(file_path):
            # Open the file and prepare it to be streamed
            response = FileResponse(open(file_path, 'rb'), content_type='audio/mp3')
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        else:
            raise Http404("File does not exist")


aai.settings.api_key = "e8fec8fa92684bcfb12a88df8e7b2346"

# class AudioTranscriptionView(APIView):
#     def post(self, request, reservation_id, *args, **kwargs):
#         try:
#             # Fetch the reservation object
#             reservation = Reservation.objects.get(id=reservation_id)
#
#             # Get the uploaded audio file from the request
#             audio_file = request.FILES['audio_file']
#
#             # Save the audio file temporarily to a path for transcription
#             temp_file_path = f'media/{reservation.name}_{reservation.restaurant}.mp3'
#             with open(temp_file_path, 'wb+') as destination:
#                 for chunk in audio_file.chunks():
#                     destination.write(chunk)
#
#             # Transcribe the audio using the AI model
#             transcriber = aai.Transcriber()
#             transcript = transcriber.transcribe(temp_file_path)
#
#             # Check for transcription errors
#             if transcript.status == aai.TranscriptStatus.error:
#                 return Response({"error": transcript.error}, status=status.HTTP_400_BAD_REQUEST)
#
#             # Save the transcription text in the speech_to_text_notes field
#             reservation.speech_to_text_notes = transcript.text
#             reservation.save()
#
#             return Response({
#                 "reservation_id": reservation.id,
#                 "speech_to_text_notes": transcript.text,
#                 "audio_file_path": temp_file_path
#             }, status=status.HTTP_200_OK)
#
#         except Reservation.DoesNotExist:
#             return Response({"detail": "Reservation not found"}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AudioView(APIView):
    def post(self, request, reservation_id, *args, **kwargs):
        try:
            # Fetch the reservation object
            reservation = Reservation.objects.get(id=reservation_id)

            # Get the uploaded audio file from the request
            audio_file = request.FILES['audio_file']

            # Save the audio file temporarily to a path for transcription
            temp_file_path = f'media/{reservation.name}_{reservation.restaurant}.mp3'
            with open(temp_file_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)

            # Transcribe the audio using the AI model
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(temp_file_path)

            # Check for transcription errors
            if transcript.status == aai.TranscriptStatus.error:
                return Response({"error": transcript.error}, status=status.HTTP_400_BAD_REQUEST)

            # Extract and parse information from the transcription text
            transcript_text = transcript.text
            reservation_time, booking_info, special_requests = self.parse_transcription_text(transcript_text)

            # Update the reservation fields
            reservation.speech_to_text_notes = transcript_text
            reservation.reservation_time = reservation_time
            reservation.booking_info = booking_info
            reservation.special_requests = special_requests
            reservation.save()

            return Response({
                "reservation_id": reservation.id,
                "speech_to_text_notes": transcript_text,
                "audio_file_path": temp_file_path
            }, status=status.HTTP_200_OK)

        except Reservation.DoesNotExist:
            return Response({"detail": "Reservation not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def parse_transcription_text(self, text):
        reservation_time = None
        booking_info = ""
        special_requests = ""

        # Extract reservation time (handles formats like "05:00 p.m." or "17:00")
        time_match = re.search(r'\b(\d{1,2}:\d{2}\s*[ap]m|\d{1,2}:\d{2})\b', text, re.IGNORECASE)
        if time_match:
            time_str = time_match.group(1).strip().lower()
            # Convert 12-hour format to 24-hour format if needed
            if 'pm' in time_str and '12' not in time_str:
                hour, minute = map(int, time_str.replace('pm', '').strip().split(':'))
                hour += 12
                time_str = f"{hour:02}:{minute:02}"
            elif 'am' in time_str and '12' in time_str:
                time_str = time_str.replace('am', '00')
            reservation_time = parse_datetime(f'1970-01-01T{time_str}:00').time()  # Using a fixed date

        word_to_number = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
            'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
            'nineteen': 19, 'twenty': 20
        }
        # Extract booking info (number of people)
        people_pattern = r'\b(?:for|reservation|booking|reserve|hold|held|occupy|get|want|table|arrive|arrival|party will include|booking for)\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s*(?:people|person|persons|childern|child|men|women|guys|lads)\b'
        people_match = re.search(people_pattern, text, re.IGNORECASE)
        if people_match:
            number_str = people_match.group(1).lower()  # Extract the matched number string
            # Convert textual number to numeric if necessary
            if number_str.isdigit():
                num_people = int(number_str)
            else:
                num_people = word_to_number.get(number_str, None)
            if num_people is not None:
                booking_info += f"Number of people: {num_people}. "

        # Extract special requests (e.g., table preferences)
        special_requests_match = re.search(r'table\s*(on the rooftop|at the front|in the front|in the centre|near|in the back|in a private|near the stage|in a envirnoment|space|near a window|by the window|outside|etc.)', text,
                                           re.IGNORECASE)
        if special_requests_match:
            special_requests = special_requests_match.group(1).strip()

        # Additional special requests handling can be added here

        return reservation_time, booking_info, special_requests

    def create_notification(reservation):
        restaurant = reservation.restaurant
        Notification.objects.create(
            restaurant=restaurant,
            reservation=reservation
        )


class NotificationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get(self, request, *args, **kwargs):
        # Get the restaurant associated with the authenticated user
        restaurant = request.user  # Since Restaurant is the custom user model

        # Fetch notifications for the restaurant
        notifications = Notification.objects.filter(restaurant=restaurant)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        # Mark all notifications as read for the restaurant associated with the authenticated user
        restaurant = request.user  # Since Restaurant is the custom user model

        # Update notifications to mark them as read
        notifications = Notification.objects.filter(restaurant=restaurant, is_read=False)
        count = notifications.update(is_read=True)
        return Response({'status': f'{count} notifications marked as read'}, status=status.HTTP_200_OK)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Add any additional context if necessary
        return context


class ThankYouAudioView(APIView):
    def get(self, request, *args, **kwargs):
        # Define the path to the audio file
        file_path = os.path.join(settings.MEDIA_ROOT, 'ElevenLabs_2024-09-19T11_11_01_Adam_pre_s50_sb75_se0_b_m2.mp3')

        # Check if the file exists
        if os.path.exists(file_path):
            # Serve the file as a response
            return FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
        else:
            # Return 404 if file not found
            raise Http404("File not found")