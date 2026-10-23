import hashlib
import hmac
import ipaddress
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.dependencies import get_db
from app.models.api_client_usage import ApiClientUsage


def get_client_ip(request: Request) -> str:
    peer_host = request.client.host if request.client is not None else None
    if peer_host is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CLIENT_IP_UNAVAILABLE",
                "message": "The client IP address could not be determined.",
            },
        )

    try:
        peer_ip = ipaddress.ip_address(peer_host)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CLIENT_IP_INVALID",
                "message": "The client IP address is invalid.",
            },
        ) from exc

    settings = get_settings()
    trusted_proxies = [
        ipaddress.ip_network(network, strict=False)
        for network in settings.TRUSTED_PROXY_IPS
    ]

    if any(peer_ip in network for network in trusted_proxies):
        forwarded_ip = request.headers.get("x-real-ip")
        try:
            peer_ip = ipaddress.ip_address(forwarded_ip or "")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "FORWARDED_CLIENT_IP_INVALID",
                    "message": "The trusted proxy did not provide a valid client IP.",
                },
            ) from exc

    if isinstance(peer_ip, ipaddress.IPv6Address):
        return str(ipaddress.ip_network((peer_ip, 64), strict=False))
    return str(peer_ip)


def _client_key(client_ip: str) -> str:
    settings = get_settings()
    secret = settings.API_LIMIT_HASH_SECRET
    salt = (
        secret.get_secret_value()
        if secret is not None
        else "ingredientiq-development-only"
    )
    return hmac.new(
        salt.encode("utf-8"),
        client_ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def apply_api_limits(
    request: Request,
    db: Session,
    *,
    count_analysis: bool,
    count_submission: bool,
) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    minute_bucket = now.replace(second=0, microsecond=0)
    daily_bucket = now.date()
    analysis_increment = int(count_analysis)
    submission_increment = int(count_submission)
    client_key = _client_key(get_client_ip(request))

    statement = insert(ApiClientUsage).values(
        client_key=client_key,
        minute_bucket=minute_bucket,
        minute_request_count=1,
        daily_bucket=daily_bucket,
        daily_analysis_count=analysis_increment,
        daily_submission_count=submission_increment,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[ApiClientUsage.client_key],
        set_={
            "minute_bucket": minute_bucket,
            "minute_request_count": case(
                (
                    ApiClientUsage.minute_bucket == minute_bucket,
                    ApiClientUsage.minute_request_count + 1,
                ),
                else_=1,
            ),
            "daily_bucket": daily_bucket,
            "daily_analysis_count": case(
                (
                    ApiClientUsage.daily_bucket == daily_bucket,
                    ApiClientUsage.daily_analysis_count
                    + analysis_increment,
                ),
                else_=analysis_increment,
            ),
            "daily_submission_count": case(
                (
                    ApiClientUsage.daily_bucket == daily_bucket,
                    ApiClientUsage.daily_submission_count
                    + submission_increment,
                ),
                else_=submission_increment,
            ),
            "updated_at": func.now(),
        },
    ).returning(
        ApiClientUsage.minute_request_count,
        ApiClientUsage.daily_analysis_count,
        ApiClientUsage.daily_submission_count,
    )

    result = db.execute(statement)
    minute_count, daily_analysis_count, daily_submission_count = result.one()
    db.commit()

    if minute_count > settings.API_REQUESTS_PER_MINUTE:
        retry_after = max(
            1,
            int(
                (
                    minute_bucket
                    + timedelta(minutes=1)
                    - now
                ).total_seconds()
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "API_RATE_LIMIT_EXCEEDED",
                "message": "Too many submissions or analysis requests. Try again shortly.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    if (
        count_analysis
        and daily_analysis_count > settings.API_DAILY_ANALYSES_PER_IP
    ):
        next_day = datetime.combine(
            daily_bucket + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        retry_after = max(1, int((next_day - now).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "DAILY_ANALYSIS_LIMIT_REACHED",
                "message": "The daily analysis limit for this IP has been reached.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    if (
        count_submission
        and daily_submission_count > settings.API_DAILY_SUBMISSIONS_PER_IP
    ):
        next_day = datetime.combine(
            daily_bucket + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        retry_after = max(1, int((next_day - now).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "DAILY_SUBMISSION_LIMIT_REACHED",
                "message": "The daily submission limit for this IP has been reached.",
            },
            headers={"Retry-After": str(retry_after)},
        )


def enforce_submission_limits(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    apply_api_limits(
        request,
        db,
        count_analysis=False,
        count_submission=True,
    )


def enforce_analysis_limits(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    apply_api_limits(
        request,
        db,
        count_analysis=True,
        count_submission=False,
    )
