from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('swipe-friends/<uuid:event_id>/', views.swipe_friends_view, name='find_friends_swipe'),
    
    # API Endpoints
    path('api/swipe-data/<uuid:event_id>/', views.api_get_swipe_data, name='api_swipe_data'),
    path('api/swipe/send/<uuid:event_id>/', views.api_send_friend_request, name='api_send_request'),
    path('api/swipe/respond/<uuid:request_id>/', views.api_respond_friend_request, name='api_respond_request'),
    path('api/swipe/list/', views.api_get_friend_requests, name='api_get_requests'),
    path('api/tutorial-seen/<uuid:event_id>/', views.api_mark_tutorial_seen, name='api_mark_tutorial_seen'),
    path('api/ocr-ktp/', views.api_ocr_ktp, name='api_ocr_ktp'),
]