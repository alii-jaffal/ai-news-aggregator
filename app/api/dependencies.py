from collections.abc import Generator

from app.database.repository import Repository


def get_repository() -> Generator[Repository, None, None]:
    repo = Repository()
    try:
        yield repo
    finally:
        repo.close()
