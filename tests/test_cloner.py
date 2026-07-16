import logging

from clone.repo_cloner import (
    RepositoryCloner,
    RepositoryAlreadyExistsError,
    RepositoryError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)

cloner = RepositoryCloner()

try:
    result = cloner.clone_repository(
        "https://github.com/iamankurraj/RepoExplorer"
    )

    print(result)

except RepositoryAlreadyExistsError:
    print("Repository already exists.")

except RepositoryError as e:
    print(e)