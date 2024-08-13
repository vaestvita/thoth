from rest_framework.authentication import TokenAuthentication


class QueryParamTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        # Try to get the token from the URL query parameter
        token = request.query_params.get("api-key")

        if not token:
            # Fall back to default token authentication
            return super().authenticate(request)

        # Authenticate the token manually
        user, token = self.authenticate_credentials(token)
        return (user, token)
