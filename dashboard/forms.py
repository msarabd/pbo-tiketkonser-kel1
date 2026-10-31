from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from ticketing.models import Venue, Event, TicketCategory

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = '__all__'
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Venue dengan Nama dan Kota ini sudah ada.",
            }
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Event dengan Nama Konser dan Tanggal ini sudah ada.",
            }
        }

class TicketCategoryForm(forms.ModelForm):
    class Meta:
        model = TicketCategory
        fields = '__all__'
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Kategori tiket ini sudah ada untuk event yang dipilih.",
            }
        }