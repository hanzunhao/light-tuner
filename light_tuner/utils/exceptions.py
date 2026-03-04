class TaskTimeoutError(Exception):
    pass


class BackendSyncError(Exception):
    pass


class ParamGenerateError(Exception):
    """
    超参数生成过程中触发的自定义异常
    用于区分超参生成阶段的错误与其他阶段（如模型训练、后端同步）的错误
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
