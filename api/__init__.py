# AceForge New UI API compatibility layer.
# Blueprints match Express routes from ace-step-ui for the ported React front end.
# No auth (local-only); all persistence via cdmf_paths global app settings.

from api.auth import bp as auth_bp
from api.songs import bp as songs_bp
from api.generate import bp as generate_bp
from api.playlists import bp as playlists_bp
from api.users import bp as users_bp
from api.contact import bp as contact_bp
from api.reference_tracks import bp as reference_tracks_bp
from api.search import bp as search_bp

__all__ = [
    "auth_bp",
    "songs_bp",
    "generate_bp",
    "playlists_bp",
    "users_bp",
    "contact_bp",
    "reference_tracks_bp",
    "search_bp",
]
