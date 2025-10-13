"""Use cases for ebook lifecycle feature."""

from backoffice.features.ebook.lifecycle.domain.usecases.approve_ebook_usecase import (
    ApproveEbookUseCase,
)
from backoffice.features.ebook.lifecycle.domain.usecases.get_stats_usecase import GetStatsUseCase
from backoffice.features.ebook.lifecycle.domain.usecases.reject_ebook_usecase import (
    RejectEbookUseCase,
)

__all__ = ["ApproveEbookUseCase", "RejectEbookUseCase", "GetStatsUseCase"]
