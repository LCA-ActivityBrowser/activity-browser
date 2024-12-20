from argparse import Namespace

from bw2data.parameters import (
    ActivityParameter,
    DatabaseParameter,
    Group,
    GroupDependency,
    ParameterBase,
    ParameterizedExchange,
    ParameterManager,
    ProjectParameter,
    parameters,
)

from activity_browser.signals import qparameter_list, qparameters

from ..patching import patch_attribute, patch_superclass, patched


class PatchedParameterBase(ParameterBase):
    """
    ParameterBase is already patched by Peewee, so we need to work more precisely by patching specific attributes
    instead of the entire class at once.
    """

    @patch_attribute(ParameterBase, "changed")
    @property
    def changed(self):
        """
        Shorthand for connecting to the parameter QUpdater. Developers can instantiate a parameter from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qparameter_list.get_or_create(self).changed

    @patch_attribute(ParameterBase, "deleted")
    @property
    def deleted(self):
        """
        Shorthand for connecting to the parameter QUpdater. Developers can instantiate a parameter from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qparameter_list.get_or_create(self).deleted

    @patch_attribute(ParameterBase, "key")
    @property
    def key(self):
        """
        Extension to get a unique key for each parameter based on group name and own name. Useful for finding the right
        QUpdater
        """
        if isinstance(self, ProjectParameter):
            return "project", self.name
        elif isinstance(self, DatabaseParameter):
            return self.database, self.name
        elif isinstance(self, ActivityParameter):
            return self.group, self.name
        return None

    @patch_attribute(ParameterBase, "delete")
    @classmethod
    def delete(cls):
        """
        We're actually patching peewee here, because the information we need is contained in the .where() call that
        follows the delete call. So we return a Namespace in which .where() is the function described below. When .where
        is called we extract what we need, emit the correct signals, and return the patched .delete().where() call.
        """

        def where(*args):
            """Patched .where() function. We use the *args to get the parameters that will be deleted from the
            database using a select() call"""
            # call the database with the where *args supplied by the user
            for param in cls.select().where(*args):
                # emit that any connected params will be changed and deleted
                [
                    qprm.emitLater("changed", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]
                [
                    qprm.emitLater("deleted", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]

            # also emit the overall qparameters
            qparameters.emitLater("parameters_changed")

            # return by calling the patched function to restore normal functionality
            return patched[ParameterBase]["delete"].__func__(cls).where(*args)

        def execute():
            """Patched .execute() function. Meaning all params are deleted. Signal accordingly"""
            # collect al params from the database
            for param in cls.select():
                # emit that any connected params will be changed and deleted
                [
                    qprm.emitLater("changed", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]
                [
                    qprm.emitLater("deleted", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]

            # also emit the overall qparameters
            qparameters.emitLater("parameters_changed")

            # return by calling the patched function to restore normal functionality
            return patched[ParameterBase]["delete"].__func__(cls).execute()

        return Namespace(where=where, execute=execute)

    @patch_attribute(ParameterBase, "update")
    @classmethod
    def update(cls, *update_args, **update_kwargs):
        """
        We're actually patching peewee here, because the information we need is contained in the .where() call that
        follows the update call. So we return a Namespace in which .where() is the function described below. When .where
        is called we extract what we need, emit the correct signals, and return the patched .update().where() call.
        """

        def where(*where_args, **where_kwargs):
            """Patched .where() function. We use the *args to get the parameters that will be updated from the
            database using a select() call"""
            # call the database with the where *args supplied by the user
            for param in cls.select().where(*where_args):
                # emit that any connected params will be changed
                [
                    qprm.emitLater("changed", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]
                [
                    qprm.emitLater("deleted", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]

            # also emit the overall qparameters
            qparameters.emitLater("parameters_changed")

            # return by calling the patched function to restore normal functionality
            return (
                patched[ParameterBase]["update"]
                .__func__(cls, *update_args, **update_kwargs)
                .where(*where_args, **where_kwargs)
            )

        def execute():
            for param in cls.select():
                # emit that any connected params will be changed
                [
                    qprm.emitLater("changed", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]
                [
                    qprm.emitLater("deleted", param)
                    for qprm in qparameter_list
                    if qprm["key"] == param.key
                ]

            # also emit the overall qparameters
            qparameters.emitLater("parameters_changed")

            # return by calling the patched function to restore normal functionality
            return (
                patched[ParameterBase]["update"]
                .__func__(cls, *update_args, **update_kwargs)
                .execute()
            )

        return Namespace(where=where, execute=execute)

    @patch_attribute(ParameterBase, "insert_many")
    @classmethod
    def insert_many(cls, *args, **kwargs):
        # emit to overall qparamaters
        qparameters.emitLater("parameters_changed")

        # return by calling the patched function to restore normal functionality
        return patched[ParameterBase]["insert_many"].__func__(cls, *args, **kwargs)

    @patch_attribute(ParameterBase, "save")
    def save(self, **kwargs):
        # call the patched function to have normal functionality
        patched[ParameterBase]["save"](self, **kwargs)

        # signal the changed parameter if it has signals connected to it
        [
            qprm.emitLater("changed", self)
            for qprm in qparameter_list
            if qprm["key"] == self.key
        ]

        # always signal through the qparameters if a parameter has changed
        qparameters.emitLater("parameters_changed")


@patch_superclass
class ParameterManager(ParameterManager):
    @property
    def parameters_changed(self):
        """
        Shorthand for connecting to the parameters QUpdater. Developers can connect directly to the parameters
        singleton, instead of importing the related QUpdater via activity_browser.signals
        """
        return qparameters.parameters_changed


parameters: ParameterManager = parameters
