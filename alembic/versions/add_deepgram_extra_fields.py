"""Add Deepgram extra fields to transcription_results

Revision ID: add_deepgram_extra_fields
Revises: 
Create Date: 2025-08-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_deepgram_extra_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to transcription_results table
    op.add_column('transcription_results', 
        sa.Column('detected_language', sa.String(10), nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('sentiment_data', postgresql.JSON, nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('topics_data', postgresql.JSON, nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('intents_data', postgresql.JSON, nullable=True))
    
    op.add_column('transcription_results', 
        sa.Column('raw_response', postgresql.JSON, nullable=True))


def downgrade():
    # Remove the columns if we need to rollback
    op.drop_column('transcription_results', 'raw_response')
    op.drop_column('transcription_results', 'intents_data')
    op.drop_column('transcription_results', 'topics_data')
    op.drop_column('transcription_results', 'sentiment_data')
    op.drop_column('transcription_results', 'detected_language')