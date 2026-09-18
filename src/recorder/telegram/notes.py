import json
from datetime import UTC, datetime

from recorder.telegram.linking import candidate_event_ids


def valid_ids(store, event_ids):
    ids = sorted({int(i) for i in event_ids})
    for event_id in ids:
        if not store.db.execute("SELECT 1 FROM timeline WHERE id=?", (event_id,)).fetchone():
            raise ValueError("unknown timeline event")
    return ids


def event_contexts(store, event_ids):
    result = []
    for event_id in event_ids:
        row = store.db.execute(
            "SELECT before_json,after_json FROM observations WHERE timeline_id=?",
            (event_id,),
        ).fetchone()
        result.append(
            {
                "event_id": event_id,
                "before": json.loads(row[0]) if row and row[0] else None,
                "after": json.loads(row[1]) if row and row[1] else None,
            }
        )
    return result


def save_text_note(
    store,
    text,
    event_ids=(),
    context=None,
    owner_id=None,
    chat_id=None,
    update_id=None,
    voice_id=None,
):
    ids = valid_ids(store, event_ids)
    with store.transaction():
        if update_id is not None:
            old = store.db.execute(
                "SELECT id FROM trader_notes WHERE telegram_update_id=?", (update_id,)
            ).fetchone()
            if old:
                return old[0]
        from recorder.events.ingestion import EventIngestor

        if context is None:
            context = {
                "event_contexts": event_contexts(store, ids),
                "at_note_time": EventIngestor(store).context(),
            }
        cur = store.db.execute(
            "INSERT INTO trader_notes(created_at,text,original_text,context_json,owner_id,chat_id,telegram_update_id,voice_id) VALUES(?,?,?,?,?,?,?,?)",
            (
                datetime.now(UTC).isoformat(),
                text,
                text,
                json.dumps(context, ensure_ascii=False),
                owner_id,
                chat_id,
                update_id,
                voice_id,
            ),
        )
        note_id = cur.lastrowid
        store.db.executemany(
            "INSERT INTO trader_note_links VALUES(?,?)", [(note_id, i) for i in ids]
        )
        store.insert_timeline(
            {
                "event_type": "VOICE_NOTE" if voice_id else "TRADER_NOTE",
                "source": "TELEGRAM",
                "source_id": str(note_id),
                "summary_ru": "Пояснение трейдера",
            }
        )
    return note_id


def links(store, note_id):
    return [
        r[0]
        for r in store.db.execute(
            "SELECT timeline_id FROM trader_note_links WHERE note_id=? ORDER BY timeline_id",
            (note_id,),
        )
    ]


def revision(store, note_id):
    return store.db.execute(
        "SELECT COUNT(*) FROM note_revisions WHERE note_id=?", (note_id,)
    ).fetchone()[0]


def verify_note(store, note_id, verified=True, *, general=False, expected_revision=None):
    with store.transaction():
        row = store.db.execute(
            "SELECT text,context_json FROM trader_notes WHERE id=?", (note_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown note")
        if expected_revision is not None and revision(store, note_id) != expected_revision:
            raise ValueError("stale note revision")
        context = json.loads(row[1]) if row[1] else {}
        if verified:
            if not (row[0] or "").strip():
                raise ValueError("Cannot verify an empty/pending transcript")
            ids = links(store, note_id)
            if bool(ids) == general:
                raise ValueError("Confirmation scope does not match event links")
            valid_ids(store, ids)
            if ids and context.get("event_contexts") != event_contexts(store, ids):
                raise ValueError("Event context is stale; relink before confirming")
            context["confirmation_scope"] = "general" if general else "event"
        else:
            context.pop("confirmation_scope", None)
        store.db.execute(
            "UPDATE trader_notes SET verified=?,context_json=? WHERE id=?",
            (int(verified), json.dumps(context, ensure_ascii=False), note_id),
        )


def revise(store, note_id, reason):
    row = store.db.execute("SELECT text FROM trader_notes WHERE id=?", (note_id,)).fetchone()
    if not row:
        raise ValueError("unknown note")
    store.db.execute(
        "INSERT INTO note_revisions(note_id,changed_at,previous_text,previous_links,reason) VALUES(?,?,?,?,?)",
        (note_id, datetime.now(UTC).isoformat(), row[0], json.dumps(links(store, note_id)), reason),
    )
    context = json.loads(
        store.db.execute("SELECT context_json FROM trader_notes WHERE id=?", (note_id,)).fetchone()[
            0
        ]
        or "{}"
    )
    context.pop("confirmation_scope", None)
    store.db.execute(
        "UPDATE trader_notes SET verified=0,context_json=? WHERE id=?",
        (json.dumps(context, ensure_ascii=False), note_id),
    )


def replace_note_links(store, note_id, event_ids):
    ids = valid_ids(store, event_ids)
    with store.transaction():
        revise(store, note_id, "links")
        store.db.execute("DELETE FROM trader_note_links WHERE note_id=?", (note_id,))
        store.db.executemany(
            "INSERT INTO trader_note_links VALUES(?,?)", [(note_id, i) for i in ids]
        )
        context = json.loads(
            store.db.execute(
                "SELECT context_json FROM trader_notes WHERE id=?", (note_id,)
            ).fetchone()[0]
            or "{}"
        )
        context.setdefault("link_context_history", []).append(
            {
                "revision": revision(store, note_id),
                "event_contexts": context.get("event_contexts", []),
            }
        )
        context["event_contexts"] = event_contexts(store, ids)
        store.db.execute(
            "UPDATE trader_notes SET context_json=? WHERE id=?",
            (json.dumps(context, ensure_ascii=False), note_id),
        )


def edit_note(store, note_id, text):
    if not text.strip():
        raise ValueError("empty note")
    with store.transaction():
        revise(store, note_id, "text")
        store.db.execute("UPDATE trader_notes SET text=? WHERE id=?", (text, note_id))


def link_candidates(store, note_at, lookback_minutes, lookforward_minutes):
    events = []
    for row in store.db.execute(
        "SELECT id,timestamp_received FROM timeline WHERE event_type IN ('ORDER','EXECUTION','POSITION')"
    ):
        try:
            events.append((row[0], datetime.fromisoformat(row[1])))
        except (ValueError, TypeError):
            continue
    return candidate_event_ids(note_at, events, lookback_minutes, lookforward_minutes)
