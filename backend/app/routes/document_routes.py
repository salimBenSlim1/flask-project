from flask import Blueprint

from ..controllers import document_controller as c
from ..middleware.auth import login_required
from ..middleware.rate_limit import rate_limit

documents_bp = Blueprint("documents", __name__)

documents_bp.post("")(login_required(c.upload_document))
documents_bp.get("")(login_required(c.list_documents))
documents_bp.get("/<int:doc_id>")(login_required(c.get_document))
documents_bp.delete("/<int:doc_id>")(login_required(c.delete_document))
documents_bp.post("/<int:doc_id>/ask")(login_required(rate_limit("ask", "ASK_RATE_LIMIT")(c.ask)))
