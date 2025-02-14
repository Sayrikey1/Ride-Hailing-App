import enum


class ActivityType(enum.Enum):
    delete = "delete"
    update = "update"
    create = "create"
    approve = "approve"
    reject = "reject"
    revert = "revert"
    activate = "activate"
    verify = "verify"
    deactivate = "deactivate"
    hard_delete = "hard_delete"
    application = "application"


class NotificationType(enum.Enum):
    email = "email"
    sms = "sms"
    push = "push"
    batch_push = "batch_push"
