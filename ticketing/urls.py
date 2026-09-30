from django.urls import path
from . import views

urlpatterns = [
    path('', views.concert_list, name='concert_list'),
    path('book/<int:category_id>/', views.book_ticket, name='book_ticket'),
    path('checkout/<int:hold_id>/', views.checkout, name='checkout'),
    path('pay/<int:hold_id>/', views.process_payment, name='process_payment'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    # Ini rute baru untuk riwayat pesanan
    path('history/', views.ticket_history, name='ticket_history'), 
]