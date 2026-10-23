from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('swipe-friends/<uuid:event_id>/', views.swipe_friends_view, name='find_friends_swipe'),
    path('api/swipe-data/<uuid:event_id>/', views.api_get_swipe_data, name='api_swipe_data'),
]