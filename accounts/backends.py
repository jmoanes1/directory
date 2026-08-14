"""Authentication backends for Employee Directory."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from accounts.forms import resolve_login_username

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate with username or registered email (including employee email).

    Django's default backend only matches the username field literally.
  """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        resolved_username = resolve_login_username(username)
        if not resolved_username:
            return None

        # Case-insensitive: get_by_natural_key is exact-match and rejects "Admin".
        user = User.objects.filter(username__iexact=resolved_username).first()
        if user is None:
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
