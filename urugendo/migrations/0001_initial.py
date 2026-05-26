"""Initial migration – create all tables

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users
    op.create_table(
        "users",
        sa.Column("id",               sa.Integer,     primary_key=True),
        sa.Column("full_name",        sa.String(120), nullable=False),
        sa.Column("phone",            sa.String(20),  unique=True, nullable=False),
        sa.Column("email",            sa.String(255), unique=True, nullable=True),
        sa.Column("hashed_password",  sa.String(255), nullable=False),
        sa.Column("is_active",        sa.Boolean,     default=True),
        sa.Column("is_verified",      sa.Boolean,     default=False),
        sa.Column("avatar_url",       sa.String(500), nullable=True),
        sa.Column("bio",              sa.Text,        nullable=True),
        sa.Column("created_at",       sa.DateTime,    nullable=False),
    )

    # Rides
    op.create_table(
        "rides",
        sa.Column("id",                 sa.Integer,     primary_key=True),
        sa.Column("driver_id",          sa.Integer,     sa.ForeignKey("users.id"), nullable=False),
        sa.Column("origin_city",        sa.String(100), nullable=False),
        sa.Column("destination_city",   sa.String(100), nullable=False),
        sa.Column("origin_detail",      sa.String(255), nullable=True),
        sa.Column("destination_detail", sa.String(255), nullable=True),
        sa.Column("departure_date",     sa.String(10),  nullable=False),
        sa.Column("departure_time",     sa.String(5),   nullable=False),
        sa.Column("total_seats",        sa.Integer,     nullable=False),
        sa.Column("available_seats",    sa.Integer,     nullable=False),
        sa.Column("price_per_seat",     sa.Integer,     nullable=False),
        sa.Column("car_model",          sa.String(100), nullable=True),
        sa.Column("car_plate",          sa.String(20),  nullable=True),
        sa.Column("tags",               sa.String(500), nullable=True),
        sa.Column("is_active",          sa.Boolean,     default=True),
        sa.Column("created_at",         sa.DateTime,    nullable=False),
    )

    # Bookings
    op.create_table(
        "bookings",
        sa.Column("id",           sa.Integer, primary_key=True),
        sa.Column("ride_id",      sa.Integer, sa.ForeignKey("rides.id"), nullable=False),
        sa.Column("passenger_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("seats_booked", sa.Integer, nullable=False),
        sa.Column("total_price",  sa.Integer, nullable=False),
        sa.Column("status",       sa.String(20), default="pending"),
        sa.Column("created_at",   sa.DateTime, nullable=False),
        sa.Column("updated_at",   sa.DateTime, nullable=False),
        sa.UniqueConstraint("ride_id", "passenger_id", name="uq_ride_passenger"),
    )

    # Payments
    op.create_table(
        "payments",
        sa.Column("id",             sa.Integer,     primary_key=True),
        sa.Column("booking_id",     sa.Integer,     sa.ForeignKey("bookings.id"), nullable=False, unique=True),
        sa.Column("provider",       sa.String(20),  nullable=False),
        sa.Column("phone_number",   sa.String(20),  nullable=False),
        sa.Column("amount",         sa.Integer,     nullable=False),
        sa.Column("currency",       sa.String(5),   default="RWF"),
        sa.Column("external_ref",   sa.String(255), nullable=True),
        sa.Column("provider_ref",   sa.String(255), nullable=True),
        sa.Column("status",         sa.String(20),  default="pending"),
        sa.Column("failure_reason", sa.Text,        nullable=True),
        sa.Column("initiated_at",   sa.DateTime,    nullable=False),
        sa.Column("completed_at",   sa.DateTime,    nullable=True),
    )

    # Ratings
    op.create_table(
        "ratings",
        sa.Column("id",            sa.Integer, primary_key=True),
        sa.Column("booking_id",    sa.Integer, sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("rater_id",      sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rated_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score",         sa.Float,   nullable=False),
        sa.Column("comment",       sa.Text,    nullable=True),
        sa.Column("created_at",    sa.DateTime, nullable=False),
        sa.UniqueConstraint("booking_id", "rater_id", name="uq_booking_rater"),
    )

    # Indexes for common queries
    op.create_index("ix_rides_origin",      "rides", ["origin_city"])
    op.create_index("ix_rides_destination", "rides", ["destination_city"])
    op.create_index("ix_rides_date",        "rides", ["departure_date"])


def downgrade():
    op.drop_table("ratings")
    op.drop_table("payments")
    op.drop_table("bookings")
    op.drop_table("rides")
    op.drop_table("users")
