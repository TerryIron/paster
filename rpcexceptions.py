#########################################################################
# 
# Copyright (c) 2015-2018  Terry Xi
# All Rights Reserved.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#########################################################################


__author__ = 'terry'


class RPCException(Exception):  

    """
    Copy from paste.httpexceptions
    Exception
      RPCException
        RPCRedirection
          * 300 - RPCMultipleChoices
          * 301 - RPCMovedPermanently
          * 302 - RPCFound
          * 303 - RPCSeeOther
          * 304 - RPCNotModified
          * 305 - RPCUseProxy
          * 306 - Unused (not implemented, obviously)
          * 307 - RPCTemporaryRedirect
        RPCError
          RPCClientError
            * 400 - RPCBadRequest
            * 401 - RPCUnauthorized
            * 402 - RPCPaymentRequired
            * 403 - RPCForbidden
            * 404 - RPCNotFound
            * 405 - RPCMethodNotAllowed
            * 406 - RPCNotAcceptable
            * 407 - RPCProxyAuthenticationRequired
            * 408 - RPCRequestTimeout
            * 409 - RPCConfict
            * 410 - RPCGone
            * 411 - RPCLengthRequired
            * 412 - RPCPreconditionFailed
            * 413 - RPCRequestEntityTooLarge
            * 414 - RPCRequestURITooLong
            * 415 - RPCUnsupportedMediaType
            * 416 - RPCRequestRangeNotSatisfiable
            * 417 - RPCExpectationFailed
          RPCServerError
            * 500 - RPCInternalServerError
            * 501 - RPCNotImplemented
            * 502 - RPCBadGateway
            * 503 - RPCServiceUnavailable
            * 504 - RPCGatewayTimeout
            * 505 - RPCVersionNotSupported
    """
    code = None
    title = None
    explanation = ''
    detail = ''
    comment = ''

    def __init__(self, detail=None, comment=None):
        assert self.code, "Do not directly instantiate abstract exceptions."
        assert isinstance(detail, (type(None), basestring)), (
            "detail must be None or a string: %r" % detail)
        assert isinstance(comment, (type(None), basestring)), (
            "comment must be None or a string: %r" % comment)
        if detail is not None:
            self.detail = detail
        if comment is not None:
            self.comment = comment
        Exception.__init__(self,"%s %s\n%s\n%s\n" % (
            self.code, self.title, self.explanation, self.detail))

    def wsgi_application(self, environ, start_response=None, exc_info=None):
        if callable(start_response):
            start_response('%s %s' % (self.code, self.title),
                           environ,
                           exc_info)
        return [environ]

    __call__ = wsgi_application


class RPCError(RPCException):
    """
    base class for status codes in the 400's and 500's

    This is an exception which indicates that an error has occurred,
    and that any work in progress should not be committed.  These are
    typically results in the 400's and 500's.
    """


class RPCRedirection(RPCException):
    """
    base class for 300's status code (redirections)

    This is an abstract base class for 3xx redirection.  It indicates
    that further action needs to be taken by the user agent in order
    to fulfill the request.  It does not necessarly signal an error
    condition.
    """

#
# 3xx Redirection
#
#  This class of status code indicates that further action needs to be
#  taken by the user agent in order to fulfill the request. The action
#  required MAY be carried out by the user agent without interaction with
#  the user if and only if the method used in the second request is GET or
#  HEAD. A client SHOULD detect infinite redirection loops, since such
#  loops generate network traffic for each redirection.
#


class RPCClientError(RPCError):
    code = 400
    title = 'Bad Request'
    explanation = ('The server could not comply with the request since\r\n'
                   'it is either malformed or otherwise incorrect.\r\n')


class RPCNotFound(RPCError):
    code = 404
    title = 'Not Found'                                                                                                                                        
    explanation = ('The resource could not be found.\r\n')
