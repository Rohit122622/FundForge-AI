

import logging
from typing import Tuple

from flask import Response, request
from flask_jwt_extended import jwt_required

from backend.utils.response import ok, error, require_json

logger = logging.getLogger("fundforge.controllers.rag")


def _get_body() -> dict:
    return request.get_json(silent=True) or {}


@jwt_required()
def retrieve() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body      = _get_body()
    query     = (body.get("query") or "").strip()
    top_k     = int(body.get("top_k", 5))
    threshold = float(body.get("score_threshold", 0.65))

    if not query:
        return error("query is required.", code=422, error_code="MISSING_FIELD")

    try:
        from backend.rag.rag_engine import get_rag_engine, RAGRetrievalConfig
        engine = get_rag_engine()
        result = engine.retrieve_context(
            query  = query,
            config = RAGRetrievalConfig(
                top_k           = top_k,
                score_threshold = threshold,
            ),
        )
        return ok(
            data={
                "retrieval_count":    result.retrieval_count,
                "included_count":     result.included_count,
                "context_text":       result.context_text,
                "citations":          result.citations.to_dict_list(),
                "processing_time_ms": result.processing_time_ms,
                "fallback_used":      result.fallback_used,
            },
            message=f"{result.included_count} knowledge chunks retrieved.",
        )
    except Exception as exc:
        logger.error("rag/retrieve error: %s", exc, exc_info=True)
        return error(f"Retrieval failed: {exc}", code=500)


@jwt_required()
def retrieve_for_profile() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body    = _get_body()
    profile = body.get("startup_profile")
    top_k   = int(body.get("top_k", 8))

    if not profile:
        return error("startup_profile is required.", code=422)

    try:
        from backend.rag.rag_engine import get_rag_engine, RAGRetrievalConfig
        engine = get_rag_engine()
        result = engine.retrieve_for_profile(
            profile_dict = profile,
            config       = RAGRetrievalConfig(top_k=top_k),
        )
        return ok(
            data={
                "retrieval_count": result.retrieval_count,
                "included_count":  result.included_count,
                "context_text":    result.context_text,
                "citations":       result.citations.to_dict_list(),
                "fallback_used":   result.fallback_used,
            },
            message=f"{result.included_count} relevant knowledge chunks retrieved.",
        )
    except Exception as exc:
        logger.error("rag/retrieve/profile error: %s", exc, exc_info=True)
        return error(f"Profile retrieval failed: {exc}", code=500)


@jwt_required()
def question_answer() -> Tuple[Response, int]:
    
    if (err := require_json(request)):
        return err

    body     = _get_body()
    question = (body.get("question") or "").strip()
    top_k    = int(body.get("top_k", 5))

    if not question:
        return error("question is required.", code=422)

    try:
        from backend.rag.rag_engine import get_rag_engine, RAGRetrievalConfig
        from backend.ibm.prompt_builder import PromptBuilder
        from backend.ibm.foundation_models import get_ai_provider, GenerationParameters

        
        rag_engine = get_rag_engine()
        rag_result = rag_engine.retrieve_context(
            query  = question,
            config = RAGRetrievalConfig(top_k=top_k, build_prompt=False),
        )

        context  = rag_result.full_context or "No relevant context found in the knowledge base."
        builder  = PromptBuilder()
        prompt   = builder.build_qa_prompt(question=question, context=context)

        params = GenerationParameters(
            max_new_tokens=600, min_new_tokens=30, temperature=0.4, top_p=0.9, top_k=30,
        )
        ai      = get_ai_provider()
        gen_res = ai.generate_text(prompt=prompt, params=params)

        return ok(
            data={
                "question":           question,
                "answer":             gen_res.text.strip(),
                "context_chunks":     rag_result.included_count,
                "citations":          rag_result.citations.to_dict_list(),
                "model_id":           gen_res.model_id,
                "fallback_used":      rag_result.fallback_used,
                "ai_metadata": {
                    "provider":          gen_res.provider,
                    "fallback_used":     gen_res.fallback_used,
                    "response_time_ms":  gen_res.response_time_ms,
                },
            },
            message="Question answered using grant knowledge base.",
        )
    except Exception as exc:
        logger.error("rag/qa error: %s", exc, exc_info=True)
        return error(f"Q&A failed: {exc}", code=500)


@jwt_required()
def stream_qa() -> Response:
    
    if (err := require_json(request)):
        return err

    body = _get_body()
    question = (body.get("question") or "").strip()
    top_k = int(body.get("top_k", 5))

    if not question:
        from backend.utils.response import error as _error
        return _error("question is required.", code=422)

    try:
        from backend.rag.rag_engine import get_rag_engine, RAGRetrievalConfig
        from backend.ibm.prompt_builder import PromptBuilder
        from backend.ibm.foundation_models import get_ai_provider, GenerationParameters
        from flask import Response

        
        rag_engine = get_rag_engine()
        rag_result = rag_engine.retrieve_context(
            query=question,
            config=RAGRetrievalConfig(top_k=top_k, build_prompt=False),
        )

        context = rag_result.full_context or "No relevant context found in the knowledge base."
        builder = PromptBuilder()
        prompt = builder.build_qa_prompt(question=question, context=context)

        params = GenerationParameters(
            max_new_tokens=600, min_new_tokens=30, temperature=0.4, top_p=0.9, top_k=30,
        )
        ai = get_ai_provider()

        def generate():
            try:
                stream = ai.generate_text_stream(prompt=prompt, params=params)
                for chunk in stream:
                    yield chunk
            except Exception as stream_exc:
                logger.error("Error during streaming token yield: %s", stream_exc)
                yield "\n[Error occurred during stream generation. Switching to offline fallback.]\n"

        return Response(generate(), mimetype="text/event-stream")
    except Exception as exc:
        logger.error("rag/stream-qa error: %s", exc, exc_info=True)
        from flask import Response
        return Response("Error initiating stream.", status=500)


def rag_health() -> Tuple[Response, int]:
    
    try:
        from backend.rag.rag_engine import get_rag_engine
        engine = get_rag_engine()
        health = engine.get_health()
        status_code = 200 if health.get("available") else 503
        return ok(data=health) if status_code == 200 else \
               error("RAG engine degraded.", code=503, details=health)
    except Exception as exc:
        logger.error("rag/health error: %s", exc, exc_info=True)
        return error("RAG health check failed.", code=500)
