"""add refresh token family tracking

Revision ID: ac15750d8e36
Revises: 91136921d325
Create Date: 2026-10-02 17:50:25.601925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = 'ac15750d8e36'
down_revision: Union[str, Sequence[str], None] = '91136921d325'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add family_id as nullable initially
    op.add_column(
        'refresh_tokens',
        sa.Column('family_id', sa.Uuid(), nullable=True)
    )

    # Backfill existing records with unique family IDs
    connection = op.get_bind()

    existing_tokens = connection.execute(
        sa.text("SELECT id FROM refresh_tokens")
    ).fetchall()

    for token in existing_tokens:
        connection.execute(
            sa.text(
                "UPDATE refresh_tokens "
                "SET family_id = :family_id WHERE id = :id"
            ),
            {
                "family_id": str(uuid.uuid4()),
                "id": token.id
            }
        )

    # Now make family_id mandatory
    op.alter_column(
        'refresh_tokens',
        'family_id',
        existing_type=sa.Uuid(),
        nullable=False
    )

    op.add_column(
        'refresh_tokens',
        sa.Column('replaced_by_id', sa.Integer(), nullable=True)
    )

    op.create_index(
        'ix_refresh_tokens_family_id',
        'refresh_tokens',
        ['family_id'],
        unique=False
    )

    op.create_foreign_key(
        'fk_refresh_tokens_replaced_by_id',
        'refresh_tokens',
        'refresh_tokens',
        ['replaced_by_id'],
        ['id']
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_refresh_tokens_replaced_by_id',
        'refresh_tokens',
        type_='foreignkey'
    )

    op.drop_index(
        'ix_refresh_tokens_family_id',
        table_name='refresh_tokens'
    )

    op.drop_column('refresh_tokens', 'replaced_by_id')
    op.drop_column('refresh_tokens', 'family_id')
