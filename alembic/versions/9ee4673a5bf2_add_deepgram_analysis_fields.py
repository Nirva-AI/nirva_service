"""Add Deepgram analysis fields

Revision ID: 9ee4673a5bf2
Revises: add_deepgram_extra_fields
Create Date: 2025-08-30 23:35:00.464916

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ee4673a5bf2'
down_revision = 'add_deepgram_extra_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to transcription_results table
    op.add_column('transcription_results', 
        sa.Column('detected_language', sa.String(10), nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('sentiment_data', sa.JSON(), nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('topics_data', sa.JSON(), nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('intents_data', sa.JSON(), nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('raw_response', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove the columns if we need to rollback
    op.drop_column('transcription_results', 'raw_response')
    op.drop_column('transcription_results', 'intents_data')
    op.drop_column('transcription_results', 'topics_data')
    op.drop_column('transcription_results', 'sentiment_data')
    op.drop_column('transcription_results', 'detected_language')