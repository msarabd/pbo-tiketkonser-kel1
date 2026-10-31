from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Tab 1: Dashboard Utama
    path('', views.dashboard_index, name='index'),

    # Tab 2: Kelola Venue
    path('venues/', views.kelola_venue, name='kelola_venue'),
    path('venues/tambah/', views.tambah_venue, name='tambah_venue'),
    path('venues/<uuid:venue_id>/edit/', views.edit_venue, name='edit_venue'),
    path('venues/<uuid:venue_id>/hapus/', views.hapus_venue, name='hapus_venue'),

    # Tab 3: Kelola Event
    path('events/', views.kelola_event, name='kelola_event'),
    path('events/tambah/', views.tambah_event, name='tambah_event'),
    path('events/<uuid:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<uuid:event_id>/hapus/', views.hapus_event, name='hapus_event'),
    path('events/<uuid:event_id>/buyers/', views.event_buyers, name='event_buyers'),
    path('events/<uuid:event_id>/forum/', views.forum_monitor, name='forum_monitor'),
    path('forum/message/<uuid:message_id>/delete/', views.delete_forum_message, name='delete_forum_message'),

    # Tab 4: Kelola Ticket Category
    path('ticket-categories/', views.kelola_ticket_kategory, name='kelola_ticket_kategory'),
    path('ticket-categories/tambah/', views.tambah_ticket_kategory, name='tambah_ticket_kategory'),
    path('ticket-categories/<uuid:category_id>/edit/', views.edit_ticket_kategory, name='edit_ticket_kategory'),
    path('ticket-categories/<uuid:category_id>/hapus/', views.hapus_ticket_kategory, name='hapus_ticket_kategory'),

    # Tab 5: Kelola User
    path('users/', views.kelola_user, name='kelola_user'),
    path('users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit_user'),
]