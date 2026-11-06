import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Max, OuterRef, Subquery
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from category.models import PriceType
from change_price.models import PriceHistory
from change_price.prefetch_helpers import prefetch_price_histories_latest
from setting.models import Log
from telegram_app.models import TelegramBot, TelegramChannel

logger = logging.getLogger(__name__)


class DashboardSummaryAPIView(APIView):

    def get(self, request):
        try:
            return self._get_summary_response()
        except Exception as exc:
            logger.exception("DashboardSummaryAPIView.get failed")
            detail = str(exc) if getattr(settings, "DEBUG", False) else ""
            payload = {
                "degraded": True,
                "detail": detail or "Summary temporarily unavailable.",
                "highest_price": 0,
                "highest_price_label": "N/A",
                "avg_24h_change": 0,
                "biggest_change": None,
                "price_changes": [],
                "total_bots": 0,
                "active_bots": 0,
                "total_channels": 0,
                "active_channels": 0,
                "total_price_types": 0,
                "total_price_updates": 0,
                "latest_update_time": None,
                "recent_updates_24h": 0,
                "last_price_update_by": None,
                "recent_price_updates": [],
            }
            return Response(payload)

    def _get_summary_response(self):
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        highest_price_obj = (
            PriceHistory.objects.defer("event_at")
            .select_related("price_type")
            .order_by("-price")
            .first()
        )
        highest_price = float(highest_price_obj.price) if highest_price_obj else 0
        highest_price_label = (
            highest_price_obj.price_type.name if highest_price_obj else "N/A"
        )

        price_changes = []
        price_types = PriceType.objects.prefetch_related(prefetch_price_histories_latest()).all()
        for pt in price_types:
            latest = pt.price_histories.first()
            if not latest:
                continue
            old = (
                pt.price_histories.filter(created_at__lte=twenty_four_hours_ago)
                .order_by("-created_at")
                .first()
            )
            if old and latest.created_at > twenty_four_hours_ago:
                current_price = float(latest.price)
                old_price = float(old.price)
                if old_price > 0:
                    change_pct = ((current_price - old_price) / old_price) * 100
                    price_changes.append({
                        "name": pt.name,
                        "current": current_price,
                        "old": old_price,
                        "change_percent": round(change_pct, 2),
                        "change_amount": round(current_price - old_price, 2),
                    })

        avg_24h_change = 0
        biggest_change = None
        if price_changes:
            avg_24h_change = round(
                sum(p["change_percent"] for p in price_changes) / len(price_changes), 2
            )
            biggest_change = max(price_changes, key=lambda x: abs(x["change_percent"]))

        total_bots = TelegramBot.objects.count()
        active_bots = TelegramBot.objects.filter(is_active=True).count()
        total_channels = TelegramChannel.objects.count()
        active_channels = TelegramChannel.objects.filter(is_active=True).count()
        total_price_types = PriceType.objects.count()
        total_price_updates = PriceHistory.objects.count()

        latest_update = PriceHistory.objects.defer("event_at").order_by("-created_at").first()
        latest_update_time = latest_update.created_at.isoformat() if latest_update else None

        recent_updates = PriceHistory.objects.filter(
            created_at__gte=twenty_four_hours_ago
        ).count()

        last_price_log = (
            Log.objects.filter(source='system')
            .filter(
                message__icontains='Price updated'
            )
            .select_related('user')
            .order_by('-created_at')
            .first()
        )
        if not last_price_log:
            last_price_log = (
                Log.objects.filter(source='system')
                .filter(message__icontains='prices updated')
                .select_related('user')
                .order_by('-created_at')
                .first()
            )
        last_price_update_by = None
        if last_price_log:
            u = last_price_log.user
            last_price_update_by = {
                "username": u.username if u else None,
                "full_name": u.get_full_name() if u else None,
                "at": last_price_log.created_at.isoformat(),
            }

        recent_updates_list = (
            PriceHistory.objects.select_related("price_type", "price_type__category")
            .order_by("-created_at")[:5]
        )
        recent_price_updates = [
            {
                "price_type": ph.price_type.name,
                "category": ph.price_type.category.name if ph.price_type.category else None,
                "price": float(ph.price),
                "updated_at": ph.created_at.isoformat(),
            }
            for ph in recent_updates_list
        ]

        return Response({
            "highest_price": highest_price,
            "highest_price_label": highest_price_label,
            "avg_24h_change": avg_24h_change,
            "biggest_change": biggest_change,
            "price_changes": price_changes,
            "total_bots": total_bots,
            "active_bots": active_bots,
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_price_types": total_price_types,
            "total_price_updates": total_price_updates,
            "latest_update_time": latest_update_time,
            "recent_updates_24h": recent_updates,
            "last_price_update_by": last_price_update_by,
            "recent_price_updates": recent_price_updates,
        })
