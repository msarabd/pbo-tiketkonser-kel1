from django.urls import path
from . import views

urlpatterns = [
    # --- Rute Publik & Katalog ---
    path('', views.EventListView.as_view(), name='event_list'),
    path('event/<uuid:event_id>/', views.EventDetailView.as_view(), name='event_detail'),

    # --- Rute Transaksi Tiket ---
    path('book/<uuid:category_id>/', views.BookTicketView.as_view(), name='book_ticket'),
    path('checkout/<uuid:order_id>/', views.CheckoutView.as_view(), name='checkout'),
    path('pay/<uuid:order_id>/', views.PayOrderView.as_view(), name='pay_order'),
    path('cancel-order/<uuid:order_id>/', views.CancelOrderView.as_view(), name='cancel_order'),
    path('success/<uuid:order_id>/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('history/', views.TicketHistoryView.as_view(), name='ticket_history'),

    # --- Rute Forum Diskusi Penonton ---
    path('forums/', views.ForumListView.as_view(), name='forum_list'),
    path('forums/<uuid:event_id>/', views.ForumRoomView.as_view(), name='forum_room'),
    path('forums/message/<uuid:message_id>/delete/', views.DeleteForumMessageView.as_view(), name='delete_forum_message'),

    # --- Rute Fitur Teman Nonton ---
    path('cari-teman/', views.ChooseFriendConcertView.as_view(), name='choose_friend_concert'),
]