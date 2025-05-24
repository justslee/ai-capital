"""create sec filings table

Revision ID: 2a3b4c5d6e7f
Revises: e13b299f59c1
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = 'e13b299f59c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sec_filings',
        sa.Column('accession_number', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('cik', sa.String(), nullable=False),
        sa.Column('filing_type', sa.String(), nullable=False),
        sa.Column('filing_date', sa.DateTime(), nullable=False),
        sa.Column('form_url', sa.String(), nullable=False),
        sa.Column('raw_html', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('accession_number')
    )
    
    # Create indexes
    op.create_index(op.f('ix_sec_filings_ticker'), 'sec_filings', ['ticker'], unique=False)
    op.create_index(op.f('ix_sec_filings_cik'), 'sec_filings', ['cik'], unique=False)
    op.create_index(op.f('ix_sec_filings_filing_type'), 'sec_filings', ['filing_type'], unique=False)
    op.create_index(op.f('ix_sec_filings_filing_date'), 'sec_filings', ['filing_date'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_sec_filings_filing_date'), table_name='sec_filings')
    op.drop_index(op.f('ix_sec_filings_filing_type'), table_name='sec_filings')
    op.drop_index(op.f('ix_sec_filings_cik'), table_name='sec_filings')
    op.drop_index(op.f('ix_sec_filings_ticker'), table_name='sec_filings')
    
    # Drop table
    op.drop_table('sec_filings') 