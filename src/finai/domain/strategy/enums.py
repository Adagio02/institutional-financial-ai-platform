from enum import StrEnum


class TradeProposalStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXECUTION_REJECTED = "execution_rejected"
    EXPIRED = "expired"
