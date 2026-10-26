from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.EditProfileView.as_view(), name='edit_profile'),
    path('swipe-friends/<uuid:event_id>/', views.SwipeFriendsView.as_view(), name='find_friends_swipe'),
    
    # API Endpoints
    path('api/swipe-data/<uuid:event_id>/', views.ApiSwipeDataView.as_view(), name='api_swipe_data'),
    path('api/swipe/send/<uuid:event_id>/', views.ApiSendFriendRequestView.as_view(), name='api_send_request'),
    path('api/swipe/respond/<uuid:request_id>/', views.ApiRespondFriendRequestView.as_view(), name='api_respond_request'),
    path('api/swipe/list/', views.ApiGetFriendRequestsView.as_view(), name='api_get_requests'),
    path('api/tutorial-seen/<uuid:event_id>/', views.ApiMarkTutorialSeenView.as_view(), name='api_mark_tutorial_seen'),
    path('api/ocr-ktp/', views.ApiOcrKtpView.as_view(), name='api_ocr_ktp'),
]