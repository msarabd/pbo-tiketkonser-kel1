from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Venue, Event, TicketCategory, Order, OrderItem, Payment, Ticket
from .forms import VenueForm, EventForm, TicketCategoryForm

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    form = VenueForm
    list_display = ('nama', 'kota')
    search_fields = ('nama', 'kota')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    form = EventForm

@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    form = TicketCategoryForm

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Ticket)