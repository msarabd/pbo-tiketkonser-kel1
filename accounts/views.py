import json
import re
import sys
import random
import requests
import pytesseract
from PIL import Image
from decouple import config
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from .models import UserProfile, FriendRequest, User
from .forms import (
    UserProfileForm, 
    CustomUserCreationForm, 
    UserEditForm, 
    MultiLoginForm, 
    ForgotPasswordForm, 
    ResetPasswordForm
)
from ticketing.models import Event, OrderItem
from .services import LocationService, SwipeMatchingService

if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    form_class = MultiLoginForm

    def get_success_url(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return str(reverse('dashboard:index'))
        return str(reverse('event_list'))
    
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False 
        
        otp = str(random.randint(100000, 999999))
        user.otp_code = otp
        user.otp_created_at = timezone.now()
        user.save() 

        fonnte_token = config('FONNTE_TOKEN') 
        try:
            response = requests.post(
                'https://api.fonnte.com/send',
                headers={
                    'Authorization': fonnte_token
                },
                data={
                    'target': user.no_hp,
                    'message': f'Kode OTP KonserKU kamu adalah {otp}. Berlaku selama 5 menit.'
                }
            )
            response_data = response.json()
            if not response_data.get('status'):
                messages.warning(self.request, f"Gagal mengirim pesan WA: {response_data.get('reason', 'Alasan tidak diketahui')}")
        except Exception as e:
            messages.error(self.request, f"Terjadi kesalahan sistem saat menghubungi API WhatsApp: {str(e)}")

        self.request.session['verify_user_id'] = str(user.id)
        return redirect('accounts:verify_wa')


class VerifyOTPView(View):
    def get(self, request):
        if 'verify_user_id' not in request.session:
            return redirect('accounts:register')
        return render(request, 'registration/verify_wa.html')

    def post(self, request):
        user_id = request.session.get('verify_user_id')
        if not user_id:
            return redirect('accounts:register')
            
        otp_input = request.POST.get('otp')
        user = get_object_or_404(User, id=user_id)

        if user.otp_code == otp_input:
            time_diff = timezone.now() - user.otp_created_at
            if time_diff.total_seconds() > 300:
                messages.error(request, "Kode OTP kedaluwarsa. Silakan daftar ulang.")
                user.delete() 
                del request.session['verify_user_id']
                return redirect('accounts:register')

            user.is_active = True
            user.otp_code = None
            user.save()
            del request.session['verify_user_id']
            
            login(request, user)
            messages.success(request, "Nomor WhatsApp berhasil diverifikasi! Selamat datang di KonserKU.")
            return redirect('event_list') 
            
        messages.error(request, "Kode OTP salah. Silakan coba lagi.")
        return render(request, 'registration/verify_wa.html')

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return render(request, 'accounts/profile.html', {'profile': profile})

class EditProfileView(LoginRequiredMixin, View):
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)
        return render(request, 'accounts/edit_profile.html', {
            'user_form': user_form,
            'form': profile_form
        })

    def post(self, request):
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
    template_name = 'accounts/swipe_friends.html'

    def dispatch(self, request, *args, **kwargs):
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
        context = super().get_context_data(**kwargs)
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)

        context['event'] = event
        context['show_tutorial'] = not profile.tutorial_seen_events.filter(id=event.id).exists()
        return context

class ApiSwipeDataView(LoginRequiredMixin, View):
    def get(self, request, event_id):
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
                'id': str(p.user.id),
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
    def _to_float(self, val):
        if val is None or val == '':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _format_requests(self, queryset, direction, my_lat, my_lon):
        formatted = []
        my_lat_val = self._to_float(my_lat)
        my_lon_val = self._to_float(my_lon)

        for req in queryset:
            target_user = req.receiver if direction == 'sent' else req.sender
            if not target_user:
                continue

            try:
                p = target_user.profile
            except (UserProfile.DoesNotExist, AttributeError):
                p, _ = UserProfile.objects.get_or_create(user=target_user)

            dist_str = "Jarak tidak diketahui"
            target_lat = self._to_float(p.latitude)
            target_lon = self._to_float(p.longitude)

            if None not in (my_lat_val, my_lon_val, target_lat, target_lon):
                try:
                    dist = LocationService.haversine_distance(
                        my_lat_val, my_lon_val, target_lat, target_lon
                    )
                    dist_str = f"{round(dist, 1)} km dari lokasimu"
                except Exception:
                    dist_str = "Jarak tidak diketahui"

            profile_pic_url = None
            if p.profile_picture:
                try:
                    profile_pic_url = p.profile_picture.url
                except Exception:
                    profile_pic_url = None

            bg_image_url = None
            if p.background_image:
                try:
                    bg_image_url = p.background_image.url
                except Exception:
                    bg_image_url = None

            event_title = req.event.nama_konser if req.event else "Konser"

            formatted.append({
                'req_id': str(req.id),
                'direction': direction,
                'status': req.status,
                'user_id': str(target_user.id),
                'username': target_user.username,
                'event_name': event_title,
                'profile_pic': profile_pic_url,
                'no_hp': target_user.no_hp if req.status in ['ACCEPTED', 'MUTUAL'] else None,
                'age': p.age or '',
                'bio': p.bio or 'Belum ada bio.',
                'gender': p.get_gender_display() or '',
                'vibe': p.get_concert_vibe_display() or '',
                'energy': p.get_social_energy_display() or '',
                'goal': p.get_matching_goal_display() or '',
                'distance': dist_str,
                'bg_image': bg_image_url
            })
        return formatted

    def get(self, request):
        try:
            my_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            my_lat = my_profile.latitude
            my_lon = my_profile.longitude

            sent = FriendRequest.objects.filter(sender=request.user).select_related('receiver__profile', 'event')
            received = FriendRequest.objects.filter(receiver=request.user).select_related('sender__profile', 'event')

            data = []
            data.extend(self._format_requests(sent, 'sent', my_lat, my_lon))
            data.extend(self._format_requests(received, 'received', my_lat, my_lon))

            return JsonResponse({'requests': data})
        except Exception as e:
            return JsonResponse({'requests': [], 'error': str(e)}, status=200)

class ApiMarkTutorialSeenView(LoginRequiredMixin, View):
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.tutorial_seen_events.add(event)
        return JsonResponse({'status': 'success'})

class ApiOcrKtpView(LoginRequiredMixin, View):
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

# ================= FITUR LUPA PASSWORD =================
class ForgotPasswordView(View):
    def get(self, request):
        form = ForgotPasswordForm()
        return render(request, 'registration/forgot_password.html', {'form': form})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            no_hp = form.cleaned_data['no_hp']
            user = User.objects.filter(no_hp=no_hp).first()

            if user:
                otp = str(random.randint(100000, 999999))
                user.otp_code = otp
                user.otp_created_at = timezone.now()
                user.save()

                fonnte_token = config('FONNTE_TOKEN') 
                try:
                    response = requests.post(
                        'https://api.fonnte.com/send',
                        headers={'Authorization': fonnte_token},
                        data={
                            'target': user.no_hp,
                            'message': f'Kode OTP Reset Password KonserKU kamu adalah {otp}. JANGAN BERIKAN KODE INI KE SIAPAPUN. Berlaku selama 5 menit.'
                        }
                    )
                except Exception:
                    messages.error(request, "Sistem gagal mengirim pesan WhatsApp.")
                    return redirect('accounts:forgot_password')

                request.session['reset_user_id'] = str(user.id)
                return redirect('accounts:verify_reset_wa')
            else:
                messages.error(request, "Nomor WhatsApp tidak terdaftar dalam sistem.")
        return render(request, 'registration/forgot_password.html', {'form': form})

class VerifyResetOTPView(View):
    def get(self, request):
        if 'reset_user_id' not in request.session:
            return redirect('accounts:forgot_password')
        return render(request, 'registration/verify_reset_wa.html')

    def post(self, request):
        user_id = request.session.get('reset_user_id')
        if not user_id:
            return redirect('accounts:forgot_password')
            
        otp_input = request.POST.get('otp')
        user = get_object_or_404(User, id=user_id)

        if user.otp_code == otp_input:
            time_diff = timezone.now() - user.otp_created_at
            if time_diff.total_seconds() > 300:
                messages.error(request, "Kode OTP kedaluwarsa. Silakan minta kode baru.")
                del request.session['reset_user_id']
                return redirect('accounts:forgot_password')

            user.otp_code = None
            user.save()
            request.session['otp_verified_for_reset'] = True 
            return redirect('accounts:set_new_password')
            
        messages.error(request, "Kode OTP salah.")
        return render(request, 'registration/verify_reset_wa.html')

class SetNewPasswordView(View):
    def get(self, request):
        if not request.session.get('otp_verified_for_reset'):
            return redirect('accounts:login')
        form = ResetPasswordForm()
        return render(request, 'registration/set_new_password.html', {'form': form})

    def post(self, request):
        if not request.session.get('otp_verified_for_reset'):
            return redirect('accounts:login')
            
        user_id = request.session.get('reset_user_id')
        user = get_object_or_404(User, id=user_id)
        
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            del request.session['reset_user_id']
            del request.session['otp_verified_for_reset']
            
            messages.success(request, "Password berhasil diubah. Silakan login dengan password baru.")
            return redirect('accounts:login')
            
        return render(request, 'registration/set_new_password.html', {'form': form})