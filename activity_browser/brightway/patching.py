import inspect
import functools
from argparse import Namespace

blacklist = ["__module__", "__subclasshook__", "__dict__", "__init_subclass__"]


def patch_superclass(cls):
    superclass = cls.__bases__[0]
    for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
        try:
            # return if the name is in the blacklist
            if name in blacklist: continue
            # return if the attribute hasn't been touched
            if value == getattr(superclass, name, None): continue

            # saving the attribute that we'll be patching
            patch_dict[superclass] = patch_dict.get(superclass, {})
            patch_dict[superclass].update({name: getattr(superclass, name, None)})

            # patching the attribute
            setattr(superclass, name, value)
        except Exception as e:
            print(e)
            pass

    return cls


def patch_attribute(obj, name):
    def inner(obj, name, fn):
        # saving the attribute that we'll be patching
        patch_dict[obj] = patch_dict.get(obj, {})
        patch_dict[obj].update({name: getattr(obj, name, None)})

        setattr(obj, name, fn)
        return

    return functools.partial(inner, obj, name)


patch_dict = {}


def patched(obj=None):
    if not obj: obj = inspect.stack()[1].frame.f_locals.get("self", None)

    if obj is None: raise ValueError("Not called for a method")
    match = [key for key in patch_dict if isinstance(obj, key)]
    if not match:
        raise ValueError("No patched attributes for this object")

    patch_namespace = Namespace()

    for name, value in patch_dict[match[0]].items():
        if hasattr(value, "__call__"):
            value = functools.partial(value, obj)
        setattr(patch_namespace, name, value)

    return patch_namespace
