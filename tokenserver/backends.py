from repoze.who.plugins.vepauth.tokenmanager import SignedTokenManager
from pyramid.threadlocal import get_current_registry

from cornice.util import json_error
from cornice.errors import Errors


class NodeAssignmentBackend(object):

    def get_node(email, service):
        """Returns the node for the given email and user.

        If no mapping is found, return None.
        """
        raise NotImplemented

    def create_node(email, service, node):
        """Sets the node for the given email, service and node"""
        raise NotImplemented


class LDAPNodeAssignmentBackend(NodeAssignmentBackend):
    """Implements a node assignment backend using simple ldap calls and relying
    on the APIs for reg/sreg otherwise
    """

    def __init__(self, ldap, sreg, snode, cache):
        self.ldap = ldap
        self.sreg = sreg
        self.snode = snode
        self.cache = cache

    def get_node(self, email, service):
        """Returns the node from the given email and user, calling LDAP
        directly.
        """
        # make a call to ldap
        # if the user does not exist, return the associated node

    def create_node(self, email, service):
        """Assign the given set of email and service to a node"""
        # make a call to the API via REST
        # adds the created mapping to the cache
        # and return the assigned Node
        # in case it fails, catch the exception and return None


class DefaultNodeAssignmentBackend(NodeAssignmentBackend):
    """Dead simple NodeAssignment backend always returning the same service
    entry. This is useful in the case we don't need to deal with multiple
    services (e.g if someone wants to setup his own tokenserver always using
    the same node
    """

    def __init__(self, service_entry=None):
        self._service_entry = service_entry

    @property
    def service_entry(self):
        """Implement this as a property to have the context when looking for
        the valiue of the setting"""
        if self._service_entry is None:
            settings = get_current_registry().settings
            self._service_entry = settings.get('tokenserver.service_entry')
        return self._service_entry

    def get_node(self, email, service):
        return self.service_entry

    def create_node(self, email, service):
        return self.service_entry


class NodeTokenManager(SignedTokenManager):
    def __init__(self, node_assignment_backend=None, *args, **kw):
        self._backend = node_assignment_backend
        super(NodeTokenManager, self).__init__(*args, **kw)

    @property
    def node_assignment_backend(self):
        """Implement this as a property so we can have the context (and this
        the settings defined when requesting it"""

        if self._backend is None:
            # try to get it from the settings
            settings = get_current_registry().settings
            self._backend = settings.get(
                    'tokenserver.node_assignment_backend',
                    DefaultNodeAssignmentBackend())

            if not isinstance(self._backend, NodeAssignmentBackend):
                self._backend = load()

        return self._backend

    def make_token(self, request, data):
        email = data['email']
        service = request.matchdict['application']

        node = self.node_assignment_backend.get_node(email, service)
        if node is None:
            node = self.node_assignment_backend.create_node(email, service)

        extra = {'service_entry': node}
        token, secret, __ = super(NodeTokenManager, self)\
                                .make_token(request, data)

        return token, secret, extra

    def _validate_request(self, request, data):
        """Raise a cornice compatible error when the application is not
        one of the defined ones"""
        if ('application' in request.matchdict and self.applications and
                request.matchdict['application'] not in self.applications):
            errors = Errors()
            errors.add("uri", "application",
            "the application %s is not defined, please use one of %s" % (
                request.matchdict['application'],
                ", ".join(self.applications)))

            raise json_error(errors, 404)