import math
from .models import UserProfile, FriendRequest

class LocationService:
    """
    Penjelasan Class: Utility class untuk komputasi spasial geografi.
    
    [OOP - ABSTRAKSI]
    Menyembunyikan kerumitan matematika dari sistem utama.
    """
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Penjelasan Method: Menghitung jarak bumi menggunakan rumus Haversine.
        
        [OOP - ENKAPSULASI]
        Method dibuat statis (@staticmethod) sehingga bisa langsung dipanggil 
        lewat `LocationService.haversine_distance()` tanpa perlu menginisialisasi objeknya.
        """
        if None in (lat1, lon1, lat2, lon2):
            return None
            
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


class SwipeMatchingService:
    """
    Penjelasan Class: Menangani logika pencarian teman ("Tinder Konser") 
    berdasarkan kepemilikan tiket dan riwayat swipe.
    """
    
    def __init__(self, user, event_id):
        """
        [OOP - ENKAPSULASI]
        Mengenkapsulasi 'state' (keadaan awal). Saat class dipanggil, ia mengunci 
        data user dan event_id ke dalam atribut lokal instance-nya.
        """
        self.user = user
        self.event_id = event_id
        self.user_profile = getattr(user, 'profile', None)

    def get_potential_matches(self):
        """
        Penjelasan Method: Mencari daftar pembeli tiket lain yang belum di-swipe.
        
        [OOP - ABSTRAKSI]
        Menyembunyikan kerumitan query `exclude()` dan perulangan Haversine dari View.
        View hanya tahu metode ini mengembalikan list of buyers.
        """
        sent_to = FriendRequest.objects.filter(
            event_id=self.event_id, sender=self.user
        ).values_list('receiver_id', flat=True)
        
        responded_to = FriendRequest.objects.filter(
            event_id=self.event_id, receiver=self.user
        ).exclude(status='PENDING').values_list('sender_id', flat=True)
        
        excluded_ids = set(sent_to) | set(responded_to)

        buyers = list(UserProfile.objects.filter(
            user__order__status='PAID',
            user__order__orderitem__category__event_id=self.event_id
        ).exclude(user=self.user).exclude(user__id__in=excluded_ids).distinct())

        my_lat = self.user_profile.latitude if self.user_profile else None
        my_lon = self.user_profile.longitude if self.user_profile else None

        for p in buyers:
            if my_lat is not None and my_lon is not None and p.latitude is not None and p.longitude is not None:
                try:
                    p.calculated_distance = LocationService.haversine_distance(
                        float(my_lat), float(my_lon), float(p.latitude), float(p.longitude)
                    )
                except TypeError:
                    p.calculated_distance = float('inf')
            else:
                p.calculated_distance = float('inf')

        buyers.sort(key=lambda x: x.calculated_distance if x.calculated_distance is not None else float('inf'))
        return buyers