from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def service_worker(request):
    # Servido em /sw.js (não /static/sw.js) para o escopo do service worker
    # cobrir o site inteiro, não só /static/.
    content = (Path(settings.BASE_DIR) / "static" / "sw.js").read_text()
    return HttpResponse(content, content_type="application/javascript")
