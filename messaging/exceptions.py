"""
    Client for AROLITEC SMS GATEWAY HTTPS API Specifications 

    The version of supported API: 2.0
    Contact: ouattaradro@gmail.com
"""


class ArolitecClientException(Exception):
    """The base exception class for all ArolitecClientExceptions"""


class ArolitecClientTypeError(ArolitecClientException, TypeError):
    def __init__(self, msg, valid_values=None, valid_classes=None):
        """Raises an exception for TypeErrors

        Args:
            msg (str): the exception message

        Keyword Args:
            valid_values (list): a list of accepted values
                                 None if unset
            valid_classes (tuple): the primitive classes that current item
                                   should be an instance of
                                   None if unset

        """
        self.valid_values = valid_values
        self.valid_classes = valid_classes
        full_msg = msg
        if valid_values:
            full_msg = "{0}. Valid values are: {1}.".format(msg, valid_values)
        if valid_classes:
            full_msg = "{0}\nValid classes are: {1}.".format(full_msg, valid_classes)
        super(ArolitecClientTypeError, self).__init__(full_msg)


class MissingArgumentError(ArolitecClientException, ValueError):
    def __init__(self, msg, argument_name=None):
        """
        Args:
            msg (str): the exception message

        Keyword Args:
            argument_name (list) the names of missing arguments. None if unset
        """

        self.argument_name = argument_name
        full_msg = msg
        if argument_name:
            full_msg = "{0}\n The following arguments are missing: {1}".format(
                msg, argument_name
            )
        super(MissingArgumentError, self).__init__(full_msg)


# class ApiAttributeError(OpenApiException, AttributeError):
#     def __init__(self, msg, path_to_item=None):
#         """
#         Raised when an attribute reference or assignment fails.

#         Args:
#             msg (str): the exception message

#         Keyword Args:
#             path_to_item (None/list) the path to the exception in the
#                 received_data dict
#         """
#         self.path_to_item = path_to_item
#         full_msg = msg
#         if path_to_item:
#             full_msg = "{0} at {1}".format(msg, render_path(path_to_item))
#         super(ApiAttributeError, self).__init__(full_msg)


# class ApiKeyError(OpenApiException, KeyError):
#     def __init__(self, msg, path_to_item=None):
#         """
#         Args:
#             msg (str): the exception message

#         Keyword Args:
#             path_to_item (None/list) the path to the exception in the
#                 received_data dict
#         """
#         self.path_to_item = path_to_item
#         full_msg = msg
#         if path_to_item:
#             full_msg = "{0} at {1}".format(msg, render_path(path_to_item))
#         super(ApiKeyError, self).__init__(full_msg)


# class ApiException(OpenApiException):
#     def __init__(self, status=None, reason=None, http_resp=None):
#         if http_resp:
#             self.status = http_resp.status
#             self.reason = http_resp.reason
#             self.body = http_resp.data
#             self.headers = http_resp.getheaders()
#         else:
#             self.status = status
#             self.reason = reason
#             self.body = None
#             self.headers = None

#     def __str__(self):
#         """Custom error messages for exception"""
#         error_message = "({0})\n" "Reason: {1}\n".format(self.status, self.reason)
#         if self.headers:
#             error_message += "HTTP response headers: {0}\n".format(self.headers)

#         if self.body:
#             error_message += "HTTP response body: {0}\n".format(self.body)

#         return error_message


# class NotFoundException(ApiException):
#     def __init__(self, status=None, reason=None, http_resp=None):
#         super(NotFoundException, self).__init__(status, reason, http_resp)


# class UnauthorizedException(ApiException):
#     def __init__(self, status=None, reason=None, http_resp=None):
#         super(UnauthorizedException, self).__init__(status, reason, http_resp)


# class ForbiddenException(ApiException):
#     def __init__(self, status=None, reason=None, http_resp=None):
#         super(ForbiddenException, self).__init__(status, reason, http_resp)


# class ServiceException(ApiException):
#     def __init__(self, status=None, reason=None, http_resp=None):
#         super(ServiceException, self).__init__(status, reason, http_resp)


# def render_path(path_to_item):
#     """Returns a string representation of a path"""
#     result = ""
#     for pth in path_to_item:
#         if isinstance(pth, int):
#             result += "[{0}]".format(pth)
#         else:
#             result += "['{0}']".format(pth)
#     return result
