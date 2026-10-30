import json
import re
import sys
import pytesseract
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy

from .models import UserProfile, FriendRequest, User
from .forms import UserProfileForm, CustomUserCreationForm, UserEditForm
from ticketing.models import Event, OrderItem
from .services import LocationService, SwipeMatchingService

# Deteksi OS otomatis untuk path binary Tesseract OCR
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class CustomLoginView(LoginView):
    """
    [OOP - INHERITANCE & POLIMORFISME]
    Menimpa LoginView bawaan Django untuk mengarahkan pengguna secara dinamis
    berdasarkan hak akses (role) tepat setelah otentikasi berhasil.
    """
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user
        # Jika akun yang masuk adalah staff/superuser, alihkan ke dashboard admin
        if user.is_staff or user.is_superuser:
            return reverse_lazy('admin_dashboard')
        
        # Pengguna biasa diarahkan ke daftar konser
        return reverse_lazy('event_list')


class RegisterView(CreateView):
    """
    Penjelasan Class: Menangani proses registrasi akun baru.

    [OOP - INHERITANCE]
    Mewarisi `CreateView` bawaan Django untuk merender dan memvalidasi formulir pendaftaran.
    """
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        """
        Penjelasan Method: Dieksekusi otomatis ketika data registrasi valid.

        [OOP - POLIMORFISME]
        Menimpa (override) metode `form_valid()` dari class induk CreateView 
        untuk menyisipkan Flash Message sebelum dialihkan ke halaman login.
        """
        messages.success(self.request, 'Akun berhasil dibuat! Silakan masuk.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Menampilkan halaman ringkasan profil pengguna yang sedang login.

    [OOP - INHERITANCE]
    Mewarisi `LoginRequiredMixin` untuk memblokir akses tanpa autentikasi, 
    dan `View` sebagai basis pemrosesan HTTP.
    """
    def get(self, request):
        # HAPUS KODE PENCEGAT ADMIN DI SINI. Biarkan admin dan user mengakses profilnya.
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return render(request, 'accounts/profile.html', {'profile': profile})

class EditProfileView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Mengelola perubahan data akun (nomor kontak) dan profil sosial.
    """
    def get(self, request):
        """
        [OOP - POLIMORFISME]
        Menyiapkan formulir UserEditForm dan UserProfileForm terisi data saat request GET.
        """
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)
        return render(request, 'accounts/edit_profile.html', {
            'user_form': user_form,
            'form': profile_form
        })

    def post(self, request):
        """
        [OOP - POLIMORFISME]
        Memproses validasi dan penyimpanan multi-form saat formulir disubmit (POST).
        """
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil dan Nomor Kontak berhasil diperbarui!')
            return redirect('accounts:profile')

        return render(request, 'accounts/edit_profile.html', {
            'user_form': user_form,
            'form': profile_form
        })


class SwipeFriendsView(LoginRequiredMixin, TemplateView):
    """
    Penjelasan Class: Mengontrol render antarmuka swipe cari teman konser ala Tinder.

    [OOP - INHERITANCE]
    Mewarisi `TemplateView` untuk rendering antarmuka HTML.
    """
    template_name = 'accounts/swipe_friends.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Penjelasan Method: Menjadi pintu gerbang izin akses sebelum template dimuat.

        [OOP - POLIMORFISME]
        Menimpa metode `dispatch()` bawaan kelas induk untuk memastikan pengguna 
        memiliki tiket lunas sebelum diperbolehkan membuka fitur cari teman.
        """
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)

        has_ticket = OrderItem.objects.filter(
            order__user=request.user,
            order__status='PAID',
            category__event=event
        ).exists()

        if not has_ticket:
            messages.error(request, "Kamu belum memiliki tiket lunas untuk konser ini.")
            return redirect('event_detail', event_id=event.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Penjelasan Method: Menyuntikkan konteks tambahan ke template.

        [OOP - POLIMORFISME]
        Menimpa `get_context_data()` untuk menyertakan objek event dan penanda tutorial.
        """
        context = super().get_context_data(**kwargs)
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)

        context['event'] = event
        context['show_tutorial'] = not profile.tutorial_seen_events.filter(id=event.id).exists()
        return context


class ApiSwipeDataView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk menyuplai daftar profil penonton lain.
    """
    def get(self, request, event_id):
        """
        [OOP - ABSTRAKSI]
        View ini mendelegasikan query filtering relasi dan kalkulasi jarak geospasial 
        ke `SwipeMatchingService`. View hanya berfokus pada format output JSON.
        """
        matching_service = SwipeMatchingService(request.user, event_id)
        buyers = matching_service.get_potential_matches()

        data = []
        for p in buyers:
            if p.calculated_distance != float('inf') and p.calculated_distance is not None:
                dist_str = f"{round(p.calculated_distance, 1)} km dari lokasimu"
            else:
                dist_str = "Jarak tidak diketahui"

            images = []
            if p.profile_picture: images.append(p.profile_picture.url)
            if p.profile_picture_2: images.append(p.profile_picture_2.url)
            if p.profile_picture_3: images.append(p.profile_picture_3.url)

            data.append({
                'id': p.user.id,
                'username': p.user.username,
                'age': p.age or '',
                'nama_ktp': p.nama_ktp or '',
                'bio': p.bio or 'Belum ada bio.',
                'gender': p.get_gender_display() or '',
                'distance': dist_str,
                'vibe': p.get_concert_vibe_display() or '',
                'energy': p.get_social_energy_display() or '',
                'goal': p.get_matching_goal_display() or '',
                'images': images,
                'bg_image': p.background_image.url if p.background_image else None
            })

        return JsonResponse({'profiles': data})


class ApiSendFriendRequestView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk mengirim permintaan swipe right (like/match).
    """
    def post(self, request, event_id):
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiver_id')
            event = get_object_or_404(Event, id=event_id)
            receiver_user = get_object_or_404(User, id=receiver_id)

            if request.user == receiver_user:
                return JsonResponse({'error': 'Tidak valid'}, status=400)

            existing_req = FriendRequest.objects.filter(
                sender=receiver_user,
                receiver=request.user,
                event=event
            ).first()

            if existing_req:
                existing_req.status = 'MUTUAL'
                existing_req.save(update_fields=['status'])
                return JsonResponse({'status': 'match', 'message': 'Cocok! (Mutual)'})
            else:
                obj, created = FriendRequest.objects.get_or_create(
                    sender=request.user,
                    receiver=receiver_user,
                    event=event,
                    defaults={'status': 'PENDING'}
                )
                return JsonResponse({'status': 'success', 'created': created})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class ApiRespondFriendRequestView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk menerima atau menolak permintaan pertemanan.
    """
    def post(self, request, request_id):
        try:
            data = json.loads(request.body)
            action = data.get('action')

            freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)

            if action == 'accept':
                freq.status = 'ACCEPTED'
            elif action == 'reject':
                freq.status = 'REJECTED'
            freq.save(update_fields=['status'])

            return JsonResponse({'status': 'success', 'new_status': freq.status})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class ApiGetFriendRequestsView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk melihat daftar permintaan masuk dan keluar.
    """
    def _format_requests(self, queryset, direction, my_lat, my_lon):
        """
        [OOP - ENKAPSULASI]
        Metode helper privat (ditandai dengan prefix underscore) untuk mengolah 
        data JSON agar tidak diekspos langsung ke luar kelas.
        """
        formatted = []
        for req in queryset:
            p = req.receiver.profile if direction == 'sent' else req.sender.profile

            dist_str = "Jarak tidak diketahui"
            if my_lat is not None and my_lon is not None and p.latitude is not None and p.longitude is not None:
                try:
                    dist = LocationService.haversine_distance(
                        float(my_lat), float(my_lon), float(p.latitude), float(p.longitude)
                    )
                    dist_str = f"{round(dist, 1)} km dari lokasimu"
                except TypeError:
                    pass

            formatted.append({
                'req_id': req.id,
                'direction': direction,
                'status': req.status,
                'user_id': p.user.id,
                'username': p.user.username,
                'event_name': req.event.nama_konser,
                'profile_pic': p.profile_picture.url if p.profile_picture else None,
                'no_hp': p.user.no_hp if req.status in ['ACCEPTED', 'MUTUAL'] else None,
                'age': p.age,
                'bio': p.bio,
                'gender': p.get_gender_display(),
                'vibe': p.get_concert_vibe_display(),
                'energy': p.get_social_energy_display(),
                'goal': p.get_matching_goal_display(),
                'distance': dist_str,
                'bg_image': p.background_image.url if p.background_image else None
            })
        return formatted

    def get(self, request):
        sent = FriendRequest.objects.filter(sender=request.user).select_related('receiver__profile', 'event')
        received = FriendRequest.objects.filter(receiver=request.user).select_related('sender__profile', 'event')

        my_profile = getattr(request.user, 'profile', None)
        my_lat = my_profile.latitude if my_profile else None
        my_lon = my_profile.longitude if my_profile else None

        data = []
        data.extend(self._format_requests(sent, 'sent', my_lat, my_lon))
        data.extend(self._format_requests(received, 'received', my_lat, my_lon))

        return JsonResponse({'requests': data})


class ApiMarkTutorialSeenView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk menandai bahwa pengguna telah melihat tutorial swipe.
    """
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.tutorial_seen_events.add(event)
        return JsonResponse({'status': 'success'})


class ApiOcrKtpView(LoginRequiredMixin, View):
    """
    Penjelasan Class: Endpoint API untuk ekstraksi 16 digit NIK dari foto KTP menggunakan Tesseract OCR.
    """
    def post(self, request):
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'Gambar tidak ditemukan'}, status=400)

        try:
            image_file = request.FILES['image']
            img = Image.open(image_file)
            text = pytesseract.image_to_string(img)
            match = re.search(r'\b\d{16}\b', text)

            if match:
                return JsonResponse({'status': 'success', 'nik': match.group()})
            else:
                return JsonResponse({'status': 'failed'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)