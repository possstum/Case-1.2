"""yandex catalog storage

Revision ID: 1c2d3e4f5a6b
Revises: 7f6b4e2c9a11
Create Date: 2026-03-18 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "1c2d3e4f5a6b"
down_revision = "7f6b4e2c9a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_column("platform_releases", "release_type_source"):
        op.add_column("platform_releases", sa.Column("release_type_source", sa.String(length=64), nullable=True))
    if not _has_column("platform_releases", "release_type_confidence"):
        op.add_column(
            "platform_releases",
            sa.Column("release_type_confidence", sa.String(length=32), nullable=True),
        )

    if not _has_table("platform_release_artists"):
        op.create_table(
            "platform_release_artists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform_release_id", sa.Integer(), nullable=False),
            sa.Column("platform_artist_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("raw_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["platform_artist_id"], ["platform_artists.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["platform_release_id"], ["platform_releases.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "platform_release_id",
                "platform_artist_id",
                "role",
                "position",
                name="uq_platform_release_artists_release_artist_role_position",
            ),
        )
        op.create_index(
            "ix_platform_release_artists_platform_artist_id",
            "platform_release_artists",
            ["platform_artist_id"],
        )
        op.create_index(
            "ix_platform_release_artists_platform_release_id",
            "platform_release_artists",
            ["platform_release_id"],
        )

    if not _has_table("platform_track_artists"):
        op.create_table(
            "platform_track_artists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform_track_id", sa.Integer(), nullable=False),
            sa.Column("platform_artist_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("raw_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["platform_artist_id"], ["platform_artists.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["platform_track_id"], ["platform_tracks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "platform_track_id",
                "platform_artist_id",
                "role",
                "position",
                name="uq_platform_track_artists_track_artist_role_position",
            ),
        )
        op.create_index(
            "ix_platform_track_artists_platform_artist_id",
            "platform_track_artists",
            ["platform_artist_id"],
        )
        op.create_index(
            "ix_platform_track_artists_platform_track_id",
            "platform_track_artists",
            ["platform_track_id"],
        )

    if not _has_table("platform_catalog_lists"):
        op.create_table(
            "platform_catalog_lists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("owner_kind", sa.String(length=32), nullable=False),
            sa.Column("owner_platform_id", sa.String(length=255), nullable=False),
            sa.Column("list_kind", sa.String(length=64), nullable=False),
            sa.Column("source_endpoint", sa.String(length=255), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("page", sa.Integer(), nullable=False),
            sa.Column("page_size", sa.Integer(), nullable=True),
            sa.Column("total_items", sa.Integer(), nullable=True),
            sa.Column("raw_json", sa.JSON(), nullable=False),
            sa.Column(
                "fetched_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "platform",
                "owner_kind",
                "owner_platform_id",
                "list_kind",
                "source_endpoint",
                "page",
                name="uq_platform_catalog_lists_owner_kind_source_page",
            ),
        )
        op.create_index(
            "ix_platform_catalog_lists_owner_kind",
            "platform_catalog_lists",
            ["platform", "owner_kind", "owner_platform_id", "list_kind"],
        )

    if not _has_table("platform_catalog_list_items"):
        op.create_table(
            "platform_catalog_list_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("catalog_list_id", sa.Integer(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("item_kind", sa.String(length=32), nullable=False),
            sa.Column("platform_artist_id", sa.Integer(), nullable=True),
            sa.Column("platform_release_id", sa.Integer(), nullable=True),
            sa.Column("platform_track_id", sa.Integer(), nullable=True),
            sa.Column("external_ref", sa.String(length=255), nullable=True),
            sa.Column("raw_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["catalog_list_id"], ["platform_catalog_lists.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["platform_artist_id"], ["platform_artists.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["platform_release_id"], ["platform_releases.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["platform_track_id"], ["platform_tracks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "catalog_list_id",
                "position",
                name="uq_platform_catalog_list_items_catalog_list_position",
            ),
        )
        op.create_index(
            "ix_platform_catalog_list_items_catalog_list_id",
            "platform_catalog_list_items",
            ["catalog_list_id"],
        )
        op.create_index(
            "ix_platform_catalog_list_items_platform_artist_id",
            "platform_catalog_list_items",
            ["platform_artist_id"],
        )
        op.create_index(
            "ix_platform_catalog_list_items_platform_release_id",
            "platform_catalog_list_items",
            ["platform_release_id"],
        )
        op.create_index(
            "ix_platform_catalog_list_items_platform_track_id",
            "platform_catalog_list_items",
            ["platform_track_id"],
        )


def downgrade() -> None:
    if _has_table("platform_catalog_list_items"):
        op.drop_index("ix_platform_catalog_list_items_platform_track_id", table_name="platform_catalog_list_items")
        op.drop_index("ix_platform_catalog_list_items_platform_release_id", table_name="platform_catalog_list_items")
        op.drop_index("ix_platform_catalog_list_items_platform_artist_id", table_name="platform_catalog_list_items")
        op.drop_index("ix_platform_catalog_list_items_catalog_list_id", table_name="platform_catalog_list_items")
        op.drop_table("platform_catalog_list_items")

    if _has_table("platform_catalog_lists"):
        op.drop_index("ix_platform_catalog_lists_owner_kind", table_name="platform_catalog_lists")
        op.drop_table("platform_catalog_lists")

    if _has_table("platform_track_artists"):
        op.drop_index("ix_platform_track_artists_platform_track_id", table_name="platform_track_artists")
        op.drop_index("ix_platform_track_artists_platform_artist_id", table_name="platform_track_artists")
        op.drop_table("platform_track_artists")

    if _has_table("platform_release_artists"):
        op.drop_index("ix_platform_release_artists_platform_release_id", table_name="platform_release_artists")
        op.drop_index("ix_platform_release_artists_platform_artist_id", table_name="platform_release_artists")
        op.drop_table("platform_release_artists")

    if _has_column("platform_releases", "release_type_confidence"):
        op.drop_column("platform_releases", "release_type_confidence")
    if _has_column("platform_releases", "release_type_source"):
        op.drop_column("platform_releases", "release_type_source")


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}
