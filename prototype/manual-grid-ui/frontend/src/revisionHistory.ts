import { AuditEvent, HistoryItem, RevisionResponse } from "./types";

export function historyItems(events: AuditEvent[], revisions: RevisionResponse[]): HistoryItem[] {
  const revisionsById = new Map(revisions.map((revision) => [revision.id, revision]));
  return events.map((event) => {
    const revision = revisionsById.get(event.entity_id ?? "");
    return { time: event.created_at, action: event.action, side: event.side ?? undefined, entityType: event.entity_type, entityId: event.entity_id, before: event.before, after: event.after, comment: revision?.comment };
  });
}
