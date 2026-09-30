from django.contrib import admin
from .models import Concert, TicketCategory, TicketHold, Order

admin.site.register(Concert)
admin.site.register(TicketCategory)
admin.site.register(TicketHold)

# Tampilkan data Order dengan rapi di panel admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')