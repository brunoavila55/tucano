from django.conf import settings


def vapid_public_key(request):
    return {"vapid_public_key": settings.WEBPUSH_VAPID_PUBLIC_KEY}
