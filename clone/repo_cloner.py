from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------

class RepositoryError(Exception):
    """Base exception for repository operations."""


class InvalidRepositoryURLError(RepositoryError):
    """Raised when the provided GitHub URL is invalid."""


class GitCommandError(RepositoryError):
    """Raised when a git command fails."""


class RepositoryAlreadyExistsError(RepositoryError):
    """Raised when attempting to clone an existing repository."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when a local repository cannot be found."""


class NotAGitRepositoryError(RepositoryError):
    """Raised when the directory is not a git repository."""


# --------------------------------------------------------------------
# Models
# --------------------------------------------------------------------

@dataclass(slots=True)
class RepositoryResult:
    success: bool
    action: str
    local_path: str
    branch: str | None
    commit_hash: str | None
    message: str


# --------------------------------------------------------------------
# Repository Cloner
# --------------------------------------------------------------------

class RepositoryCloner:
    """
    Tool responsible ONLY for:

    - Cloning GitHub repositories
    - Updating existing repositories

    """

    URL_PATTERN = re.compile(
        r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
    )

    def __init__(
        self,
        workspace: str = "workspace/repos",
        timeout: int = 120,
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    # -------------------------------------------------------------

    def clone_repository(self, repo_url: str) -> RepositoryResult:
        """
        Clone a GitHub repository.
        """

        owner, repo = self._validate_url(repo_url)

        repo_path = self.workspace / repo

        if repo_path.exists():
            raise RepositoryAlreadyExistsError(
                f"{repo} already exists."
            )

        logger.info("Cloning %s", repo_url)

        self._run_git(
            [
                "git",
                "clone",
                repo_url,
                str(repo_path),
            ]
        )

        return RepositoryResult(
            success=True,
            action="cloned",
            local_path=str(repo_path),
            branch=self._current_branch(repo_path),
            commit_hash=self._latest_commit(repo_path),
            message="Repository cloned successfully.",
        )

    # -------------------------------------------------------------

    def update_repository(self, local_path: str) -> RepositoryResult:
        """
        Update an existing repository.
        """

        repo = Path(local_path)

        if not repo.exists():
            raise RepositoryNotFoundError(local_path)

        if not (repo / ".git").exists():
            raise NotAGitRepositoryError(local_path)

        logger.info("Updating repository %s", local_path)

        self._run_git(
            [
                "git",
                "-C",
                str(repo),
                "pull",
            ]
        )

        return RepositoryResult(
            success=True,
            action="updated",
            local_path=str(repo),
            branch=self._current_branch(repo),
            commit_hash=self._latest_commit(repo),
            message="Repository updated successfully.",
        )

    # -------------------------------------------------------------

    def delete_repository(self, local_path: str):
        """
        Remove a repository from disk.
        """

        repo = Path(local_path)

        if repo.exists():
            shutil.rmtree(repo)

            logger.info("Deleted repository %s", repo)

    # -------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------

    def _validate_url(self, url: str):

        match = self.URL_PATTERN.match(url)

        if not match:
            raise InvalidRepositoryURLError(
                "Invalid GitHub repository URL."
            )

        return match.groups()

    # -------------------------------------------------------------

    def _run_git(self, command: list[str]):

        try:

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

        except subprocess.TimeoutExpired as e:
            raise GitCommandError(
                "Git command timed out."
            ) from e

        except subprocess.CalledProcessError as e:
            raise GitCommandError(
                e.stderr.strip()
            ) from e

    # -------------------------------------------------------------

    def _current_branch(self, repo: Path) -> str | None:

        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "branch",
                "--show-current",
            ],
            capture_output=True,
            text=True,
        )

        return result.stdout.strip() or None

    # -------------------------------------------------------------

    def _latest_commit(self, repo: Path) -> str | None:

        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
        )

        return result.stdout.strip() or None