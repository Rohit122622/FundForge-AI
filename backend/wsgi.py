

import logging
import os

from backend.app import create_app

logger = logging.getLogger("fundforge.wsgi")



application = create_app(config_name=os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting development server on port %d", port)
    application.run(host="0.0.0.0", port=port)
