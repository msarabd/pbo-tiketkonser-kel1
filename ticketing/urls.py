from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('event/<uuid:event_id>/', views.event_detail, name='event_detail'),
    path('book/<uuid:category_id>/', views.book_ticket, name='book_ticket'),
    path('checkout/<uuid:order_id>/', views.checkout, name='checkout'),
    # Dua kabel baru:
    path('pay/<uuid:order_id>/', views.pay_order, name='pay_order'),
    path('history/', views.ticket_history, name='ticket_history'),
]