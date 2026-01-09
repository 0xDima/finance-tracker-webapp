from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import ImportSession, StagingTransaction


def cleanup_old_draft_imports(db: Session, days: int = 7) -> int:
    """
    Delete draft import sessions (and staging rows) older than the given number of days.
    Returns the number of sessions removed.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    stale_sessions = (
        db.query(ImportSession)
        .filter(ImportSession.status == "draft", ImportSession.created_at < cutoff)
        .all()
    )

    if not stale_sessions:
        return 0

    import_ids = [sess.id for sess in stale_sessions]
    db.query(StagingTransaction).filter(StagingTransaction.import_id.in_(import_ids)).delete(
        synchronize_session=False
    )
    db.query(ImportSession).filter(ImportSession.id.in_(import_ids)).delete(
        synchronize_session=False
    )
    db.commit()
    return len(import_ids)
