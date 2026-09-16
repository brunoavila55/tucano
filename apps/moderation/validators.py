from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_MB = 5


def validate_file_size(file):
    limit = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Arquivo maior que {MAX_UPLOAD_SIZE_MB}MB não é permitido.")
