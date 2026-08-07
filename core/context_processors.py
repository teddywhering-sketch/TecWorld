def role_context(request):
    user = request.user
    is_secretaria = user.is_authenticated and user.groups.filter(name="Secretaria").exists()
    try:
        from core.models import ConfiguracaoSistema
        config = ConfiguracaoSistema.load()
        logo_url = config.logo.url if config.logo else None
    except Exception:
        logo_url = None
    return {"is_secretaria": is_secretaria, "is_operacional": user.is_authenticated and (user.is_staff or is_secretaria), "config_logo_url": logo_url}
