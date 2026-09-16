from .models import AuditEvent


def log_event(actor, event_type, obj, **metadata):
    AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        event_type=event_type,
        object_repr=str(obj),
        metadata=metadata,
    )
