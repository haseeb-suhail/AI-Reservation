from django.urls import path
from ai_reservation.urls import schema_view
from .views import SignupView, LoginView, RestaurantProfileView, PublicProfileView, ServeAudioFileView, ThankYouAudioView, AudioView, NotificationView
urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', RestaurantProfileView.as_view(), name='profile'),
    path('restaurants/<uuid:unique_url>/profile/', PublicProfileView.as_view(), name='restaurant-public-profile'),  # Public profile view
    path('profile/notifications/', RestaurantProfileView.as_view(), name='notification-mark-read'), #use post with empty body to mark all the notifications as read
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('serve-audio/<str:file_name>/', ServeAudioFileView.as_view(), name='serve-audio-file'),
    path('reservations/<int:reservation_id>/transcribe/', AudioView.as_view(), name='audio-transcription'),
    path('notifications/', NotificationView.as_view(), name='notification-list'),
    path('thank-you/', ThankYouAudioView.as_view(), name='play-thank-you'),
]


