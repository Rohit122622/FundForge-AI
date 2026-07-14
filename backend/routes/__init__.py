

from backend.routes.auth_routes import auth_bp
from backend.routes.document_routes import documents_bp
from backend.routes.grant_routes import grants_bp
from backend.routes.proposal_routes import proposals_bp
from backend.routes.rag_routes import rag_bp
from backend.routes.eligibility_routes import eligibility_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.profile_routes import profile_bp
from backend.routes.tracker_routes import tracker_bp
from backend.routes.search_routes import search_bp
from backend.routes.system_routes import system_bp

__all__ = [
    "auth_bp",
    "documents_bp",
    "grants_bp",
    "proposals_bp",
    "rag_bp",
    "eligibility_bp",
    "dashboard_bp",
    "profile_bp",
    "tracker_bp",
    "search_bp",
    "system_bp",
]
