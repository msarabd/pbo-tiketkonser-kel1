from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Venue, Event, TicketCategory

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)

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