"""fleet mechanic: ai_traces + prompt_patches

Revision ID: a1b2c3d4e5f6
Revises: 13df8f5cdd90
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '13df8f5cdd90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ai_traces',
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('span_id', sa.String(), nullable=True),
        sa.Column('vessel_id', sa.String(), nullable=True),
        sa.Column('crew_id', sa.String(), nullable=True),
        sa.Column('route', sa.String(), nullable=False),
        sa.Column('model_role', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('user_prompt', sa.Text(), nullable=True),
        sa.Column('input_data', sa.Text(), nullable=True),
        sa.Column('rag_sources', sa.Text(), nullable=True),
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('latency_ms', sa.String(), nullable=True),
        sa.Column('token_count', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('uploaded_to_arize', sa.Boolean(), nullable=True),
        sa.Column('eval_label', sa.String(), nullable=True),
        sa.Column('eval_score', sa.String(), nullable=True),
        sa.Column('eval_explanation', sa.Text(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "eval_label IN ('correct','hallucinated','unsupported','unsafe','unevaluated')",
            name='ck_trace_eval_label',
        ),
        sa.PrimaryKeyConstraint('trace_id'),
    )
    op.create_table(
        'prompt_patches',
        sa.Column('patch_id', sa.String(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('target_route', sa.String(), nullable=False),
        sa.Column('target_model_role', sa.String(), nullable=False),
        sa.Column('failure_summary', sa.Text(), nullable=True),
        sa.Column('proposed_patch', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('pushed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('drafted','queued','pushed','rejected')",
            name='ck_patch_status',
        ),
        sa.ForeignKeyConstraint(['trace_id'], ['ai_traces.trace_id'], ),
        sa.PrimaryKeyConstraint('patch_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('prompt_patches')
    op.drop_table('ai_traces')
