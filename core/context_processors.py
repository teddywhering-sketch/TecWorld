def role_context(request):
    user = request.user
    is_secretaria = user.is_authenticated and user.groups.filter(name="Secretaria").exists()
    try:
        from core.models import ConfiguracaoSistema
        config = ConfiguracaoSistema.load()
        logo_url = config.logo.url if config.logo else None
    except Exception:
        logo_url = None
    is_provedor = user.is_authenticated and user.groups.filter(name="Provedor").exists()
    import shutil
    try:
        total, used, free = shutil.disk_usage("/")
        disk_total = total / (1024**3)
        disk_used = used / (1024**3)
        disk_free = free / (1024**3)
        disk_percent = (used / total) * 100
    except:
        disk_total = disk_used = disk_free = disk_percent = 0

    return {"is_secretaria": is_secretaria, "is_operacional": user.is_authenticated and (user.is_staff or is_secretaria), "is_provedor": is_provedor, "config_logo_url": logo_url, "disk_total": disk_total, "disk_used": disk_used, "disk_free": disk_free, "disk_percent": disk_percent}

