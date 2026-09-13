"""
Sync registered connector manifests into the DB on startup.
Keeps the connectors table current with what's actually installed.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_sdk.registry import all_manifests
from app.models.connector import Connector
from app.models.flow import Flow
from app.models.run import Run, RunStep
from app.models.user import User

# Fixed dev user — created at startup when no auth middleware is wired yet
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def seed_dev_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    if result.scalar_one_or_none() is None:
        db.add(User(
            id=DEV_USER_ID,
            email="dev@nexus.local",
            role="admin",
            is_active=True,
        ))
        await db.commit()


async def seed_admin_user(db: AsyncSession) -> None:
    """Ensure a human admin account with login credentials exists."""
    from app.config import settings
    from app.services.auth import hash_password

    result = await db.execute(select(User).where(User.email == settings.admin_email))
    user = result.scalar_one_or_none()
    if user is None:
        db.add(User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        ))
        await db.commit()


# Names of old demo flows that should be removed and replaced.
_OLD_DEMO_NAMES = {
    "GitHub PR → Jira Task",
    "Daily DB Health Report → Teams",
    "API Uptime Monitor",
    "Zendesk Ticket → Jira Bug",
    "Kubernetes Pod Failure Alert",
    # Previous version used CoinGecko/CoinCap which fail inside Docker
    "Bitcoin Price Pulse",
}

# All five flows use only public, auth-free APIs so they work with zero configuration.
_DEMO_FLOWS: list[dict] = [
    # ── 1. Cat Fact of the Day ─────────────────────────────────────────────────
    {
        "name": "Cat Fact of the Day",
        "description": (
            "Every day at 9 AM, fetch a random cat fact from catfact.ninja "
            "and transform it into a structured daily briefing."
        ),
        "status": "active",
        "graph_json": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "connector_key": "cron",
                    "config_json": {"action_key": "scheduled", "cron_expression": "0 9 * * *"},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "http-1",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://catfact.ninja/fact",
                        "method": "GET",
                        "timeout_seconds": 10,
                    },
                    "position": {"x": 100, "y": 260},
                },
                {
                    "id": "code-1",
                    "type": "action",
                    "connector_key": "code",
                    "config_json": {
                        "action_key": "run_python",
                        "source_code": "\n".join([
                            "import datetime",
                            "body = inputs.get('body', {})",
                            "fact = body.get('fact', 'No fact available')",
                            "length = body.get('length', 0)",
                            "now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')",
                            "output = {",
                            "    'fact': fact,",
                            "    'character_count': length,",
                            "    'fetched_at': now,",
                            "    'summary': f'Cat fact ({length} chars): {fact}',",
                            "}",
                        ]),
                    },
                    "position": {"x": 100, "y": 420},
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "http-1"},
                {"id": "e2", "source": "http-1", "target": "code-1"},
            ],
        },
    },
    # ── 2. Bitcoin Price Pulse ─────────────────────────────────────────────────
    {
        "name": "Bitcoin Price Pulse",
        "description": (
            "Every 15 minutes, fetch the live Bitcoin price from Blockchain.info "
            "and compute a formatted price snapshot."
        ),
        "status": "active",
        "graph_json": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "connector_key": "cron",
                    "config_json": {"action_key": "scheduled", "cron_expression": "*/15 * * * *"},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "http-1",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://blockchain.info/ticker",
                        "method": "GET",
                        "timeout_seconds": 10,
                    },
                    "position": {"x": 100, "y": 260},
                },
                {
                    "id": "code-1",
                    "type": "action",
                    "connector_key": "code",
                    "config_json": {
                        "action_key": "run_python",
                        "source_code": "\n".join([
                            "usd = inputs.get('body', {}).get('USD', {})",
                            "price = float(usd.get('last', 0))",
                            "buy = float(usd.get('buy', 0))",
                            "sell = float(usd.get('sell', 0))",
                            "spread = round(sell - buy, 2)",
                            "output = {",
                            "    'asset': 'Bitcoin (BTC)',",
                            "    'price_usd': round(price, 2),",
                            "    'bid_usd': round(buy, 2),",
                            "    'ask_usd': round(sell, 2),",
                            "    'spread_usd': spread,",
                            "    'summary': f'BTC ${price:,.2f} USD (bid ${buy:,.2f} / ask ${sell:,.2f})',",
                            "}",
                        ]),
                    },
                    "position": {"x": 100, "y": 420},
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "http-1"},
                {"id": "e2", "source": "http-1", "target": "code-1"},
            ],
        },
    },
    # ── 3. ISS Live Position ───────────────────────────────────────────────────
    {
        "name": "ISS Live Position Tracker",
        "description": (
            "Every 5 minutes, query the International Space Station's current "
            "coordinates, altitude and speed from the wheretheiss.at API."
        ),
        "status": "active",
        "graph_json": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "connector_key": "cron",
                    "config_json": {"action_key": "scheduled", "cron_expression": "*/5 * * * *"},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "http-1",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://api.wheretheiss.at/v1/satellites/25544",
                        "method": "GET",
                        "timeout_seconds": 10,
                    },
                    "position": {"x": 100, "y": 260},
                },
                {
                    "id": "code-1",
                    "type": "action",
                    "connector_key": "code",
                    "config_json": {
                        "action_key": "run_python",
                        "source_code": "\n".join([
                            "d = inputs.get('body', {})",
                            "lat = round(float(d.get('latitude', 0)), 4)",
                            "lon = round(float(d.get('longitude', 0)), 4)",
                            "alt = round(float(d.get('altitude', 0)), 1)",
                            "vel = round(float(d.get('velocity', 0)), 1)",
                            "vis = d.get('visibility', 'unknown')",
                            "output = {",
                            "    'latitude': lat,",
                            "    'longitude': lon,",
                            "    'altitude_km': alt,",
                            "    'speed_kmh': vel,",
                            "    'visibility': vis,",
                            "    'summary': f'ISS at {lat}, {lon} — {alt} km altitude, {vel} km/h, {vis}',",
                            "}",
                        ]),
                    },
                    "position": {"x": 100, "y": 420},
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "http-1"},
                {"id": "e2", "source": "http-1", "target": "code-1"},
            ],
        },
    },
    # ── 4. Webhook → Joke + Cat Fact Combo ────────────────────────────────────
    {
        "name": "Webhook Joke & Cat Fact Combo",
        "description": (
            "Triggered by any inbound webhook, fetches a random joke from JokeAPI "
            "and a cat fact in parallel, then combines them into a single response payload."
        ),
        "status": "active",
        "graph_json": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "connector_key": "webhook",
                    "config_json": {"action_key": "inbound"},
                    "position": {"x": 300, "y": 60},
                },
                {
                    "id": "http-joke",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode",
                        "method": "GET",
                        "timeout_seconds": 10,
                    },
                    "position": {"x": 100, "y": 220},
                },
                {
                    "id": "http-cat",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://catfact.ninja/fact",
                        "method": "GET",
                        "timeout_seconds": 10,
                    },
                    "position": {"x": 500, "y": 220},
                },
                {
                    "id": "code-1",
                    "type": "action",
                    "connector_key": "code",
                    "config_json": {
                        "action_key": "run_python",
                        "source_code": "\n".join([
                            "# inputs contains merged outputs from both upstream HTTP nodes",
                            "joke_body = inputs.get('body', {})",
                            "joke = joke_body.get('joke', '')",
                            "cat_fact = inputs.get('fact', 'No cat fact available')",
                            "output = {",
                            "    'joke': joke,",
                            "    'joke_category': joke_body.get('category', 'unknown'),",
                            "    'cat_fact': cat_fact,",
                            "    'summary': f'Joke: {joke} | Cat fact: {cat_fact}',",
                            "}",
                        ]),
                    },
                    "position": {"x": 300, "y": 400},
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "http-joke"},
                {"id": "e2", "source": "trigger-1", "target": "http-cat"},
                {"id": "e3", "source": "http-joke", "target": "code-1"},
                {"id": "e4", "source": "http-cat", "target": "code-1"},
            ],
        },
    },
    # ── 5. SpaceX Next Launch Brief ────────────────────────────────────────────
    {
        "name": "SpaceX Next Launch Brief",
        "description": (
            "Every Monday morning, fetch the next upcoming SpaceX launch from "
            "the public SpaceX API and produce a structured mission briefing."
        ),
        "status": "active",
        "graph_json": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger",
                    "connector_key": "cron",
                    "config_json": {"action_key": "scheduled", "cron_expression": "0 8 * * 1"},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "http-1",
                    "type": "action",
                    "connector_key": "http_rest",
                    "config_json": {
                        "action_key": "request",
                        "url": "https://api.spacexdata.com/v5/launches/next",
                        "method": "GET",
                        "timeout_seconds": 15,
                    },
                    "position": {"x": 100, "y": 260},
                },
                {
                    "id": "code-1",
                    "type": "action",
                    "connector_key": "code",
                    "config_json": {
                        "action_key": "run_python",
                        "source_code": "\n".join([
                            "import datetime",
                            "launch = inputs.get('body', {})",
                            "name = launch.get('name', 'Unknown')",
                            "date_unix = launch.get('date_unix') or 0",
                            "details = (launch.get('details') or 'No details available')[:300]",
                            "if date_unix:",
                            "    dt = datetime.datetime.utcfromtimestamp(date_unix)",
                            "    date_str = dt.strftime('%Y-%m-%d %H:%M UTC')",
                            "else:",
                            "    date_str = launch.get('date_utc', 'TBD')",
                            "rocket_id = launch.get('rocket', 'unknown')",
                            "launchpad_id = launch.get('launchpad', 'unknown')",
                            "output = {",
                            "    'mission': name,",
                            "    'launch_date': date_str,",
                            "    'rocket_id': rocket_id,",
                            "    'launchpad_id': launchpad_id,",
                            "    'details': details,",
                            "    'summary': f'Next SpaceX launch: {name} on {date_str}',",
                            "}",
                        ]),
                    },
                    "position": {"x": 100, "y": 420},
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "http-1"},
                {"id": "e2", "source": "http-1", "target": "code-1"},
            ],
        },
    },
]


async def seed_demo_flows(db: AsyncSession) -> None:
    """Replace old demo flows and insert the zero-config public-API demo set."""
    # Remove any old demo flows from previous versions (cascade delete runs first).
    old_flows = (await db.execute(
        select(Flow).where(Flow.name.in_(_OLD_DEMO_NAMES))
    )).scalars().all()
    if old_flows:
        old_ids = [f.id for f in old_flows]
        run_ids = (await db.execute(
            select(Run.id).where(Run.flow_id.in_(old_ids))
        )).scalars().all()
        if run_ids:
            await db.execute(sa_delete(RunStep).where(RunStep.run_id.in_(run_ids)))
            await db.execute(sa_delete(Run).where(Run.flow_id.in_(old_ids)))
        for old in old_flows:
            await db.delete(old)
    await db.flush()

    # Upsert: insert each demo flow only if it doesn't exist yet by name.
    for spec in _DEMO_FLOWS:
        result = await db.execute(select(Flow).where(Flow.name == spec["name"]))
        if result.scalar_one_or_none() is None:
            db.add(Flow(
                name=spec["name"],
                description=spec["description"],
                version=1,
                status=spec["status"],
                graph_json=spec["graph_json"],
                created_by=DEV_USER_ID,
            ))
    await db.commit()


async def sync_connectors(db: AsyncSession) -> None:
    manifests = all_manifests()
    for key, manifest in manifests.items():
        result = await db.execute(select(Connector).where(Connector.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            db.add(Connector(
                key=key,
                name=manifest.get("name", key),
                category=manifest.get("category", "generic"),
                manifest_version=manifest.get("version", "1.0.0"),
                icon_url=manifest.get("icon_url"),
                description=manifest.get("description"),
            ))
        else:
            row.name = manifest.get("name", key)
            row.category = manifest.get("category", "generic")
            row.manifest_version = manifest.get("version", "1.0.0")
            row.icon_url = manifest.get("icon_url")
            row.description = manifest.get("description")
    await db.commit()
