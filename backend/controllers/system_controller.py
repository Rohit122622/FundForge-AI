

import logging
from typing import Tuple
from flask import Response

from backend.utils.response import ok, error
from backend.ibm import get_ai_provider, FallbackManager

logger = logging.getLogger("fundforge.controllers.system")

def get_ai_status() -> Tuple[Response, int]:
    
    try:
        provider = get_ai_provider()
        fallback_chain = ["IBM", "Gemini", "Grok"]
        
        ibm_healthy = False
        gemini_healthy = False
        grok_healthy = False
        
        if isinstance(provider, FallbackManager):
            try:
                ibm_healthy = provider._ibm.is_healthy()
            except Exception:
                pass
            try:
                gemini_healthy = provider._gemini.is_healthy()
            except Exception:
                pass
            try:
                grok_healthy = provider._grok.is_healthy()
            except Exception:
                pass
                
            last_active = provider.last_active_provider
            fallback_used = provider.last_fallback_used
            resp_time = provider.last_response_time_ms
        else:
            p_name = provider.provider_name.upper()
            if p_name == "IBM":
                ibm_healthy = provider.is_healthy()
            elif p_name == "GEMINI":
                gemini_healthy = provider.is_healthy()
            elif p_name == "GROK":
                grok_healthy = provider.is_healthy()
                
            last_active = p_name
            fallback_used = False
            resp_time = 0.0

        health_status = {
            "IBM": ibm_healthy,
            "Gemini": gemini_healthy,
            "Grok": grok_healthy
        }
        
        
        primary = "IBM"
        if not ibm_healthy:
            if gemini_healthy:
                primary = "Gemini"
            elif grok_healthy:
                primary = "Grok"
            else:
                primary = "None"
        
        return ok(
            data={
                "current_primary_provider": primary,
                "fallback_chain": fallback_chain,
                "provider_health": health_status,
                "last_active_provider": last_active,
                "fallback_used": fallback_used,
                "response_time_ms": resp_time
            },
            message="AI status retrieved successfully."
        )
    except Exception as exc:
        logger.error("Failed to retrieve AI status: %s", exc, exc_info=True)
        return error(f"Failed to retrieve AI status: {exc}", code=500)
