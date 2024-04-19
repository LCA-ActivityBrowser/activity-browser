from bw2data.parameters import *

from argparse import Namespace

from activity_browser.signals import qparameter_list, qparameters
from ..patching import patch_attribute, patch_dict, patch_superclass


class PatchedParameterBase(ParameterBase):
    """
    ParameterBase is already patched by Peewee, so we need to work more precisely by patching specific attributes
    instead of the entire class at once.
    """

    @patch_attribute(ParameterBase, "changed")
    @property
    def changed(self):
        return qparameter_list.get_or_create(self).changed

    @patch_attribute(ParameterBase, "deleted")
    @property
    def deleted(self):
        return qparameter_list.get_or_create(self).deleted

    @patch_attribute(ParameterBase, "key")
    @property
    def key(self):
        if isinstance(self, ProjectParameter): return "project", self.name
        elif isinstance(self, DatabaseParameter): return self.database, self.name
        elif isinstance(self, ActivityParameter): return self.group, self.name
        return None

    @patch_attribute(ParameterBase, "delete")
    @classmethod
    def delete(cls):
        def where(*args):
            for param in cls.select().where(*args):
                [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
                [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
            qparameters.emitLater("parameters_changed")
            return patch_dict[ParameterBase]["delete"].__func__(cls).where(*args)

        def execute():
            for param in cls.select():
                [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
                [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
            qparameters.emitLater("parameters_changed")
            return patch_dict[ParameterBase]["delete"].__func__(cls).execute()

        return Namespace(where=where, execute=execute)

    @patch_attribute(ParameterBase, "update")
    @classmethod
    def update(cls, *update_args, **update_kwargs):
        def where(*where_args, **where_kwargs):
            for param in cls.select().where(*where_args):
                [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
                [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
            qparameters.emitLater("parameters_changed")
            return patch_dict[ParameterBase]["update"].__func__(cls, *update_args, **update_kwargs).where(*where_args, **where_kwargs)

        def execute():
            for param in cls.select():
                [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
                [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
            qparameters.emitLater("parameters_changed")
            return patch_dict[ParameterBase]["update"].__func__(cls, *update_args, **update_kwargs).execute()

        return Namespace(where=where, execute=execute)

    # @patch_attribute(ParameterBase, "create")
    # @classmethod
    # def create(cls):
    #     def where(*args):
    #         for param in cls.select().where(*args):
    #             [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
    #             [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
    #         qparameters.emitLater("parameters_changed")
    #         return patch_dict[ParameterBase]["delete"].__func__(cls).where(*args)
    #
    #     def execute():
    #         for param in cls.select():
    #             [qprm.emitLater("changed", param) for qprm in qparameter_list if qprm["key"] == param.key]
    #             [qprm.emitLater("deleted", param) for qprm in qparameter_list if qprm["key"] == param.key]
    #
    #         return patch_dict[ParameterBase]["delete"].__func__(cls).execute()
    #
    #     return Namespace(where=where, execute=execute)

    @patch_attribute(ParameterBase, "insert_many")
    @classmethod
    def insert_many(cls, *args, **kwargs):
        qparameters.emitLater("parameters_changed")
        return patch_dict[ParameterBase]["insert_many"].__func__(cls, *args, **kwargs)

    @patch_attribute(ParameterBase, "save")
    def save(self, **kwargs):
        patch_dict[ParameterBase]["save"](self, **kwargs)
        [qprm.emitLater("changed", self) for qprm in qparameter_list if qprm["key"] == self.key]
        qparameters.emitLater("parameters_changed")


@patch_superclass
class ParameterManager(ParameterManager):
    @property
    def parameters_changed(self):
        return qparameters.parameters_changed


parameters: ParameterManager = parameters

