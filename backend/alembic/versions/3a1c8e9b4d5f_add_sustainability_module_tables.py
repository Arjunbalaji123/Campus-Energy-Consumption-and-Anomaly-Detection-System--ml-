"""Add Sustainability Module Tables (Configs, Targets, Verifications).

Revision ID: 3a1c8e9b4d5f
Revises: 24f28f8caf92
Create Date: 2026-10-17 20:15:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1c8e9b4d5f'
down_revision: Union[str, None] = '24f28f8caf92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create sustainability_configs table
    op.create_table(
        'sustainability_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=250), nullable=False),
        sa.Column('effective_date', sa.String(length=50), nullable=False),
        sa.Column('applicable_region', sa.String(length=150), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sustainability_configs_config_key'), 'sustainability_configs', ['config_key'], unique=True)
    op.create_index(op.f('ix_sustainability_configs_id'), 'sustainability_configs', ['id'], unique=False)

    # 2. Create sustainability_targets table
    op.create_table(
        'sustainability_targets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('building_id', sa.Integer(), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('target_reduction_pct', sa.Float(), nullable=False),
        sa.Column('baseline_period_start', sa.DateTime(), nullable=False),
        sa.Column('baseline_period_end', sa.DateTime(), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('target_completion_date', sa.DateTime(), nullable=False),
        sa.Column('current_measured_progress_pct', sa.Float(), nullable=False),
        sa.Column('current_measured_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('last_calculated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sustainability_targets_building_id'), 'sustainability_targets', ['building_id'], unique=False)
    op.create_index(op.f('ix_sustainability_targets_id'), 'sustainability_targets', ['id'], unique=False)
    op.create_index(op.f('ix_sustainability_targets_name'), 'sustainability_targets', ['name'], unique=False)
    op.create_index(op.f('ix_sustainability_targets_status'), 'sustainability_targets', ['status'], unique=False)

    # 3. Create sustainability_verifications table
    op.create_table(
        'sustainability_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=False),
        sa.Column('baseline_period_start', sa.DateTime(), nullable=False),
        sa.Column('baseline_period_end', sa.DateTime(), nullable=False),
        sa.Column('baseline_avg_kwh', sa.Float(), nullable=False),
        sa.Column('post_action_period_start', sa.DateTime(), nullable=False),
        sa.Column('post_action_period_end', sa.DateTime(), nullable=False),
        sa.Column('post_action_avg_kwh', sa.Float(), nullable=False),
        sa.Column('observed_reduction_kwh', sa.Float(), nullable=False),
        sa.Column('observed_reduction_pct', sa.Float(), nullable=False),
        sa.Column('cost_savings_inr', sa.Float(), nullable=False),
        sa.Column('emissions_reduction_kg_co2e', sa.Float(), nullable=False),
        sa.Column('verification_status', sa.String(length=30), nullable=False),
        sa.Column('verification_criteria', sa.Text(), nullable=False),
        sa.Column('verified_by', sa.String(length=100), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sustainability_verifications_id'), 'sustainability_verifications', ['id'], unique=False)
    op.create_index(op.f('ix_sustainability_verifications_recommendation_id'), 'sustainability_verifications', ['recommendation_id'], unique=False)
    op.create_index(op.f('ix_sustainability_verifications_verification_status'), 'sustainability_verifications', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sustainability_verifications_verification_status'), table_name='sustainability_verifications')
    op.drop_index(op.f('ix_sustainability_verifications_recommendation_id'), table_name='sustainability_verifications')
    op.drop_index(op.f('ix_sustainability_verifications_id'), table_name='sustainability_verifications')
    op.drop_table('sustainability_verifications')

    op.drop_index(op.f('ix_sustainability_targets_status'), table_name='sustainability_targets')
    op.drop_index(op.f('ix_sustainability_targets_name'), table_name='sustainability_targets')
    op.drop_index(op.f('ix_sustainability_targets_id'), table_name='sustainability_targets')
    op.drop_index(op.f('ix_sustainability_targets_building_id'), table_name='sustainability_targets')
    op.drop_table('sustainability_targets')

    op.drop_index(op.f('ix_sustainability_configs_id'), table_name='sustainability_configs')
    op.drop_index(op.f('ix_sustainability_configs_config_key'), table_name='sustainability_configs')
    op.drop_table('sustainability_configs')

