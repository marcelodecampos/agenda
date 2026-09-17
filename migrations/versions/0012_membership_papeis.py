"""Create the Membership<->Papel association table.

Fixes a critical access-control bug: without this table, every read of a
membership attached the entire Papel catalog to it, granting the union of
every role's permissions to any user with any membership.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_membership_papeis"
down_revision: Union[str, Sequence[str], None] = "0011_tipos_procedimento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "membership_papeis" not in inspector.get_table_names():
        op.create_table(
            "membership_papeis",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("membership_id", sa.String(), nullable=False),
            sa.Column("papel_id", sa.String(), nullable=False),
            sa.UniqueConstraint(
                "membership_id", "papel_id", name="uq_membership_papel"
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "membership_papeis" in inspector.get_table_names():
        op.drop_table("membership_papeis")
