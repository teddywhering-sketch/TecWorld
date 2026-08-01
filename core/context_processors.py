def role_context(request):
    user = request.user
    is_secretaria = user.is_authenticated and user.groups.filter(name="Secretaria").exists()
    return {"is_secretaria": is_secretaria, "is_operacional": user.is_authenticated and (user.is_staff or is_secretaria)}
