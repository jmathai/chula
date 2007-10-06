"""
Chula helper module for working with web services
"""

from chula import error, json, collection

class Transport(collection.RestrictedCollection):
    """
    Web service transport class designed to be subclassed to provide
    various means of encoding.
    """

    def __validkeys__(self):
        """
        Populate the supported keys
        """

        return ('data',
                'exception',
                'msg',
                'success')

    def __defaults__(self):
        """
        Set reasonable defaults
        """

        self.data = None
        self.exception = None
        self.msg = None
        self.success = False

class JSON(Transport):
    """
    Webservice that uses json as the transport layer
    """

    def encode(self):
        """
        Encode the transport into a json string
        """

        return json.encode(self)