"""Module containing functions to parse and validate input sources and patterns."""

from __future__ import annotations

import re
import uuid
import warnings
from pathlib import Path
from urllib.parse import unquote, urlparse

from gitingest.config import TMP_BASE_PATH
from gitingest.schemas import IngestionQuery
from gitingest.utils.exceptions import InvalidPatternError
from gitingest.utils.git_utils import check_repo_exists, fetch_remote_branches_or_tags
from gitingest.utils.ignore_patterns import DEFAULT_IGNORE_PATTERNS
from gitingest.utils.query_parser_utils import (
    KNOWN_GIT_HOSTS,
    _get_user_and_repo_from_path,
    _is_valid_git_commit_hash,
    _is_valid_pattern,
    _validate_host,
    _validate_url_scheme,
)


async def parse_query(
    source: str,
    *,
    max_file_size: int,
    from_web: bool,
    include_patterns: set[str] | str | None = None,
    ignore_patterns: set[str] | str | None = None,
    token: str | None = None,
) -> IngestionQuery:
    """Parse the input source to extract details for the query and process the include and ignore patterns.

    Parameters
    ----------
    source : str
        The source URL or file path to parse.
    max_file_size : int
        The maximum file size in bytes to include.
    from_web : bool
        Flag indicating whether the source is a web URL.
    include_patterns : set[str] | str | None
        Patterns to include. Can be a set of strings or a single string.
    ignore_patterns : set[str] | str | None
        Patterns to ignore. Can be a set of strings or a single string.
    token : str | None
        GitHub personal access token (PAT) for accessing private repositories.

    Returns
    -------
    IngestionQuery
        A dataclass object containing the parsed details of the repository or file path.

    """
    query = _parse_local_dir_path(source)

    # Combine default ignore patterns + custom patterns
    ignore_patterns_set = DEFAULT_IGNORE_PATTERNS.copy()
    if ignore_patterns:
        ignore_patterns_set.update(_parse_patterns(ignore_patterns))

    # Process include patterns and override ignore patterns accordingly
    if include_patterns:
        parsed_include = _parse_patterns(include_patterns)
        # Override ignore patterns with include patterns
        ignore_patterns_set = set(ignore_patterns_set) - set(parsed_include)
    else:
        parsed_include = None

    return IngestionQuery(
        user_name=query.user_name,
        repo_name=query.repo_name,
        url=query.url,
        subpath=query.subpath,
        local_path=query.local_path,
        slug=query.slug,
        id=query.id,
        type=query.type,
        branch=query.branch,
        commit=query.commit,
        max_file_size=max_file_size,
        ignore_patterns=ignore_patterns_set,
        include_patterns=parsed_include,
    )


def _parse_patterns(pattern: set[str] | str) -> set[str]:
    """Parse and validate file/directory patterns for inclusion or exclusion.

    Takes either a single pattern string or set of pattern strings and processes them into a normalized list.
    Patterns are split on commas and spaces, validated for allowed characters, and normalized.

    Parameters
    ----------
    pattern : set[str] | str
        Pattern(s) to parse - either a single string or set of strings

    Returns
    -------
    set[str]
        A set of normalized patterns.

    Raises
    ------
    InvalidPatternError
        If any pattern contains invalid characters. Only alphanumeric characters,
        dash (-), underscore (_), dot (.), forward slash (/), plus (+), and
        asterisk (*) are allowed.

    """
    patterns = pattern if isinstance(pattern, set) else {pattern}

    parsed_patterns: set[str] = set()
    for p in patterns:
        parsed_patterns = parsed_patterns.union(set(re.split(",| ", p)))

    # Remove empty string if present
    parsed_patterns = parsed_patterns - {""}

    # Normalize Windows paths to Unix-style paths
    parsed_patterns = {p.replace("\\", "/") for p in parsed_patterns}

    # Validate and normalize each pattern
    for p in parsed_patterns:
        if not _is_valid_pattern(p):
            raise InvalidPatternError(p)

    return parsed_patterns


def _parse_local_dir_path(path_str: str) -> IngestionQuery:
    """Parse the given file path into a structured query dictionary.

    Parameters
    ----------
    path_str : str
        The file path to parse.

    Returns
    -------
    IngestionQuery
        A dictionary containing the parsed details of the file path.

    """
    path_obj = Path(path_str).resolve()
    slug = path_obj.name if path_str == "." else path_str.strip("/")
    return IngestionQuery(local_path=path_obj, slug=slug, id=str(uuid.uuid4()))
