from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Venue, Event, TicketCategory, Seat, Order, OrderItem, Payment, Ticket

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Menambahkan field kustom (no_hp dan is_organizer) ke halaman edit user
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan PBO', {'fields': ('no_hp', 'is_organizer')}),
    )
    # Menambahkan field kustom ke halaman tambah user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Tambahan PBO', {'fields': ('no_hp', 'is_organizer')}),
    )

# Pendaftaran tabel lainnya
admin.site.register(Venue)
admin.site.register(Event)
admin.site.register(TicketCategory)
admin.site.register(Seat)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Ticket)