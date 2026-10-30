from django.urls import path
from . import views

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    
    # --- Rute Dasbor Admin Kustom ---
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-forum/<uuid:event_id>/', views.AdminForumMonitorView.as_view(), name='admin_forum_monitor'),
    path('admin-forum/message/<uuid:message_id>/delete/', views.AdminDeleteForumMessageView.as_view(), name='admin_delete_forum_message'),
    
    # --- Rute CRUD Khusus Front-End Admin ---
    path('admin-dashboard/venue/add/', views.AdminVenueCreateView.as_view(), name='admin_venue_add'),
    path('admin-dashboard/venue/<uuid:pk>/edit/', views.AdminVenueUpdateView.as_view(), name='admin_venue_edit'),
    path('admin-dashboard/venue/<uuid:pk>/delete/', views.AdminVenueDeleteView.as_view(), name='admin_venue_delete'),
    
    path('admin-dashboard/event/add/', views.AdminEventCreateView.as_view(), name='admin_event_add'),
    path('admin-dashboard/event/<uuid:pk>/edit/', views.AdminEventUpdateView.as_view(), name='admin_event_edit'),
    path('admin-dashboard/event/<uuid:pk>/delete/', views.AdminEventDeleteView.as_view(), name='admin_event_delete'),
    
    path('admin-dashboard/ticket-category/add/', views.AdminTicketCategoryCreateView.as_view(), name='admin_ticket_category_add'),
    path('admin-dashboard/ticket-category/<uuid:pk>/edit/', views.AdminTicketCategoryUpdateView.as_view(), name='admin_ticket_category_edit'),
    path('admin-dashboard/ticket-category/<uuid:pk>/delete/', views.AdminTicketCategoryDeleteView.as_view(), name='admin_ticket_category_delete'),

    # --- Rute Publik & User Biasa ---
    path('event/<uuid:event_id>/', views.EventDetailView.as_view(), name='event_detail'),
    path('book/<uuid:category_id>/', views.BookTicketView.as_view(), name='book_ticket'),
    path('checkout/<uuid:order_id>/', views.CheckoutView.as_view(), name='checkout'),
    path('pay/<uuid:order_id>/', views.PayOrderView.as_view(), name='pay_order'),
    path('cancel-order/<uuid:order_id>/', views.CancelOrderView.as_view(), name='cancel_order'),
    path('success/<uuid:order_id>/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('history/', views.TicketHistoryView.as_view(), name='ticket_history'),
    path('forums/', views.ForumListView.as_view(), name='forum_list'),
    path('forums/<uuid:event_id>/', views.ForumRoomView.as_view(), name='forum_room'),
    path('forums/message/<uuid:message_id>/delete/', views.DeleteForumMessageView.as_view(), name='delete_forum_message'),
    path('cari-teman/', views.ChooseFriendConcertView.as_view(), name='choose_friend_concert'),
    path('admin-dashboard/event/<uuid:event_id>/buyers/', views.AdminEventBuyersView.as_view(), name='admin_event_buyers'),
    path('admin-dashboard/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin-dashboard/users/<uuid:user_id>/delete/', views.AdminUserDeleteView.as_view(), name='admin_user_delete'),
]