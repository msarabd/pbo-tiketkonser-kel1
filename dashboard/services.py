from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from accounts.models import User
from ticketing.models import Event, Venue, OrderItem, Order

class DashboardAnalyticsService:
    @staticmethod
    def get_summary_metrics():
        return {
            'total_event': Event.objects.count(),
            'total_venue': Venue.objects.count(),
            'total_anggota': User.objects.filter(is_staff=False).count(),
            'total_terjual': OrderItem.objects.filter(order__status='PAID').count()
        }

    @staticmethod
    def get_sales_trend(days=7):
        sekarang = timezone.now()
        batas_waktu = (sekarang - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        penjualan = (
            OrderItem.objects.filter(order__status='PAID', order__waktu_pesan__gte=batas_waktu)
            .annotate(tanggal=TruncDate('order__waktu_pesan'))
            .values('tanggal')
            .annotate(jumlah=Count('id'))
            .order_by('tanggal')
        )
        
        data_map = {item['tanggal']: item['jumlah'] for item in penjualan}
        labels = []
        data = []
        
        for i in range(days):
            tgl = (batas_waktu + timedelta(days=i)).date()
            labels.append(tgl.strftime('%d %b'))
            data.append(data_map.get(tgl, 0))
            
        return labels, data

    @staticmethod
    def get_top_events(limit=5):
        return (
            Event.objects.annotate(
                total_terjual=Count('ticketcategory__orderitem', filter=Q(ticketcategory__orderitem__order__status='PAID'))
            )
            .filter(total_terjual__gt=0)
            .order_by('-total_terjual')[:limit]
        )

    @staticmethod
    def get_recent_transactions(limit=5):
        return (
            Order.objects.filter(status='PAID')
            .select_related('user')
            .prefetch_related('orderitem_set__category__event')
            .order_by('-waktu_pesan')[:limit]
        )

class DashboardModerationService:
    @staticmethod
    def delete_event_safely(event):
        """
        Mencegah penghapusan event jika sudah ada tiket yang dibayar lunas.
        Ini krusial untuk menjaga integritas data riwayat pembelian.
        """
        has_paid_tickets = OrderItem.objects.filter(
            category__event=event, 
            order__status='PAID'
        ).exists()
        
        if has_paid_tickets:
            raise ValueError(
                f"Event '{event.nama_konser}' tidak bisa dihapus karena sudah memiliki tiket terjual (PAID). "
                "Hapus data secara keras ditolak untuk mencegah kerusakan data transaksi."
            )
        event.delete()