from sqlalchemy import text

from finai.infrastructure.database.engine import engine


def test_database_connection() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_alembic_version_table_exists() -> None:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'alembic_version'
        )
        """
    )

    with engine.connect() as connection:
        exists = connection.execute(query).scalar_one()

    assert exists is True


def test_pipeline_run_table_exists() -> None:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'pipeline_run'
        )
        """
    )

    with engine.connect() as connection:
        exists = connection.execute(query).scalar_one()

    assert exists is True