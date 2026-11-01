"""Public error categories, independent of HTTP, SQL or identity SDKs."""


class ApplicationError(Exception):
    code = "application_error"
    message = "请求无法完成"
    status = 400


class Unauthenticated(ApplicationError):
    code = "authentication_required"
    message = "需要有效的服务端身份会话"
    status = 401


class AccessDenied(ApplicationError):
    code = "permission_denied"
    message = "无权访问请求的工厂范围"
    status = 403


class NotFound(ApplicationError):
    code = "not_found"
    message = "未找到可访问的资源"
    status = 404


class InvalidRequest(ApplicationError):
    code = "invalid_request"
    message = "请求参数无效"
    status = 422


class StorageUnavailable(ApplicationError):
    code = "storage_unavailable"
    message = "查询服务暂不可用"
    status = 503


class IdentityUnavailable(ApplicationError):
    code = "identity_provider_unavailable"
    message = "身份接入渠道尚未配置"
    status = 503
