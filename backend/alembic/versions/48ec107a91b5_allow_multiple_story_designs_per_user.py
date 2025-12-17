from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql as sql

# revision identifiers, used by Alembic.
revision = 'allow_multiple_story_designs'
down_revision = 'd7cb0114c5dd'
branch_labels = None
depends_on = None


def upgrade():
    # 1. create temporary table without UNIQUE constraint
    op.execute("""
    CREATE TABLE story_designs_new (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        user_face_filename VARCHAR NOT NULL,
        pages_json TEXT NOT NULL,
        status VARCHAR DEFAULT 'pending_admin',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """)

    # 2. copy data from old table
    op.execute("""
    INSERT INTO story_designs_new (id, user_id, user_face_filename, pages_json, status, created_at, updated_at)
    SELECT id, user_id, user_face_filename, pages_json, status, created_at, updated_at
    FROM story_designs;
    """)

    # 3. drop old table
    op.execute("DROP TABLE story_designs;")

    # 4. rename new table
    op.execute("ALTER TABLE story_designs_new RENAME TO story_designs;")


def downgrade():
    # Re-create the old table with UNIQUE constraint
    op.execute("""
    CREATE TABLE story_designs_old (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE,
        user_face_filename VARCHAR NOT NULL,
        pages_json TEXT NOT NULL,
        status VARCHAR DEFAULT 'pending_admin',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """)

    op.execute("""
    INSERT INTO story_designs_old (id, user_id, user_face_filename, pages_json, status, created_at, updated_at)
    SELECT id, user_id, user_face_filename, pages_json, status, created_at, updated_at
    FROM story_designs;
    """)

    op.execute("DROP TABLE story_designs;")
    op.execute("ALTER TABLE story_designs_old RENAME TO story_designs;")
