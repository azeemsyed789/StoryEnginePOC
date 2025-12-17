from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
import logging
from sqlalchemy import delete

logger = logging.getLogger(__name__)

try:
    from models import UploadedAsset, StoryDesign
except Exception:
    from backend.models import UploadedAsset, StoryDesign


def delete_user_face_assets(
    user_id: int, db: Session, upload_dir: Optional[Path] = None
) -> int:
    """
    Delete all uploaded assets of type 'face' for the given user and remove the files
    from disk. Returns the number of deleted assets.
    """
    if upload_dir is None:
        BASE_DIR = Path(__file__).resolve().parents[1]
        upload_dir = BASE_DIR / "static" / "uploads"

    filenames = [
        a.filename
        for a in db.query(UploadedAsset.filename)
        .filter(UploadedAsset.type == "face", UploadedAsset.user_id == user_id)
        .all()
    ]

    deleted_files = 0
    for fname in filenames:
        try:
            file_path = upload_dir / fname
            if file_path.exists():
                file_path.unlink()
                deleted_files += 1
        except Exception as e:
            logger.info(f"Failed deleting file {fname}: {e}")

    deleted_rows = (
        db.query(UploadedAsset)
        .filter(UploadedAsset.type == "face", UploadedAsset.user_id == user_id)
        .delete(synchronize_session=False)
    )
    if deleted_rows > 0:
        db.commit()

    logger.info(
        f"Deleted {deleted_rows} DB records and {deleted_files} files for user {user_id}"
    )
    return deleted_rows


def delete_other_user_designs(
    user_id: int,
    db: Session,
    # keep_design_id: Optional[int] = None,
) -> int:
    """
    Delete all StoryDesign rows for `user_id` except `keep_design_id`.
    Returns number of deleted rows.
    """

    stmt = delete(StoryDesign).where(StoryDesign.user_id == user_id)

    # if keep_design_id is not None:
    #     stmt = stmt.where(StoryDesign.id != keep_design_id)

    result = db.execute(stmt)
    db.commit()

    deleted = result.rowcount or 0

    logger.info(
        f"Deleted {deleted} story designs for user {user_id}"
    )
    return deleted
