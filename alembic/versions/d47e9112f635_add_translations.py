"""Add translations

Revision ID: d47e9112f635
Revises: 9596ec0e704b
Create Date: 2017-01-27 12:10:08.522696

"""

# revision identifiers, used by Alembic.
revision = 'd47e9112f635'
down_revision = '9596ec0e704b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column('climatechangerecommendation', sa.Column('text_es', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('climatechangerecommendation', sa.Column('text_fr', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('hazardcategory', sa.Column('general_recommendation_es', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('hazardcategory', sa.Column('general_recommendation_fr', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('technicalrecommendation', sa.Column('detail_es', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('technicalrecommendation', sa.Column('detail_fr', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('technicalrecommendation', sa.Column('text_es', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('technicalrecommendation', sa.Column('text_fr', sa.Unicode(), nullable=True), schema='datamart')


def downgrade(engine_name):
    op.drop_column('technicalrecommendation', 'text_fr', schema='datamart')
    op.drop_column('technicalrecommendation', 'text_es', schema='datamart')
    op.drop_column('technicalrecommendation', 'detail_fr', schema='datamart')
    op.drop_column('technicalrecommendation', 'detail_es', schema='datamart')
    op.drop_column('hazardcategory', 'general_recommendation_fr', schema='datamart')
    op.drop_column('hazardcategory', 'general_recommendation_es', schema='datamart')
    op.drop_column('climatechangerecommendation', 'text_fr', schema='datamart')
    op.drop_column('climatechangerecommendation', 'text_es', schema='datamart')
