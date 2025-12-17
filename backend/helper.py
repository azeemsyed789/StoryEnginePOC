from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

try:
    from models import UploadedAsset
except Exception:
    from backend.models import UploadedAsset


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

    assets = (
        db.query(UploadedAsset)
        .filter(UploadedAsset.type == "face", UploadedAsset.user_id == user_id)
        .all()
    )
    deleted = 0
    for a in assets:
        try:
            file_path = upload_dir / a.filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"⚠️ Failed deleting file {a.filename}: {e}")

        try:
            db.delete(a)
            deleted += 1
        except Exception as e:
            print(f"⚠️ Failed deleting DB record for {a.filename}: {e}")

    if deleted > 0:
        db.commit()

    print(f"✅ Deleted {deleted} face assets for user {user_id}")
    return deleted
