from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-wa/', views.VerifyOTPView.as_view(), name='verify_wa'), 

    # Rute Lupa Password
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-reset-wa/', views.VerifyResetOTPView.as_view(), name='verify_reset_wa'),
    path('set-new-password/', views.SetNewPasswordView.as_view(), name='set_new_password'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.EditProfileView.as_view(), name='edit_profile'),
    
    path('swipe/<uuid:event_id>/', views.SwipeFriendsView.as_view(), name='swipe_friends'),
    
    path('api/swipe-data/<uuid:event_id>/', views.ApiSwipeDataView.as_view(), name='api_swipe_data'),
    path('api/send-friend-request/<uuid:event_id>/', views.ApiSendFriendRequestView.as_view(), name='api_send_friend_request'),
    path('api/respond-friend-request/<uuid:request_id>/', views.ApiRespondFriendRequestView.as_view(), name='api_respond_friend_request'),
    path('api/friend-requests/', views.ApiGetFriendRequestsView.as_view(), name='api_friend_requests'),
    path('api/mark-tutorial-seen/<uuid:event_id>/', views.ApiMarkTutorialSeenView.as_view(), name='api_mark_tutorial_seen'),
    path('api/ocr-ktp/', views.ApiOcrKtpView.as_view(), name='api_ocr_ktp'),
]