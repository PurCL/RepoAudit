class RepoAuditError(Exception):
    """Base class for all errors related to RepoAudit."""

    pass


class RAValueError(RepoAuditError, ValueError):
    """Exception raised for value errors in RepoAudit."""

    pass


class RATypeError(RepoAuditError, TypeError):
    """Exception raised for type errors in RepoAudit."""

    pass


class RAAnalysisError(RepoAuditError):
    """Exception raised for analysis errors in RepoAudit."""

    pass
