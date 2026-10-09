from knox.auth import TokenAuthentication


class KnoxOrDemoTokenAuthentication(TokenAuthentication):
    """
    Authentification de l'API par jeton Knox (POST /api/users/login).

    Seul un jeton Knox valide, non expiré et d'un compte actif authentifie la requête. Un jeton
    absent, invalide ou expiré laisse la requête anonyme : la garde centrale
    (autorisations/garde.py) répond alors 401, sauf sur les routes publiques (connexion).
    L'ancien repli « administrateur par défaut » et les jetons de démonstration sont supprimés :
    ils donnaient les droits d'administrateur à toute requête sans jeton.
    (Le nom de la classe est conservé : elle est citée par de nombreuses vues.)
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except Exception:
            # Jeton refusé : requête anonyme, la garde décide (401 ou route publique)
            return None
