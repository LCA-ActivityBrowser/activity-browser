import functools

blacklist = ["__module__", "__subclasshook__", "__dict__", "__init_subclass__"]


def patch_superclass(cls):
    """
    Class decorator that will patch any methods that differ from the superclass onto said superclass during runtime.
    """
    # collect the superclass
    superclass = cls.__bases__[0]

    # iterate over the attributes in the decorated class
    for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
        try:
            # return if the name is in the blacklist
            if name in blacklist:
                continue

            # return if the attribute is the same as the one in the superclass
            if value == getattr(superclass, name, None):
                continue

            # saving the attribute that we'll be patching
            patched[superclass] = patched.get(superclass, {})
            patched[superclass].update({name: getattr(superclass, name, None)})

            # patching the attribute
            setattr(superclass, name, value)
        except Exception as e:
            # an exception will be interesting, but patching shouldn't break, so continue.
            print(e)
            pass

    return cls


def patch_attribute(obj, name):
    """
    Product decorator to patch single attributes of a class. Handy when the superclass is already patched by
    another library and will be too different to use patch_superclass on. Pass the class you want to patch as argument
    """

    def inner(obj, name, fn):
        # saving the attribute that we'll be patching
        patched[obj] = patched.get(obj, {})
        patched[obj].update({name: getattr(obj, name, None)})

        setattr(obj, name, fn)
        return

    return functools.partial(inner, obj, name)


class Patched(dict):
    def __getitem__(self, obj):
        """
        We subclass this method because we also want subclasses to work for this.
        """
        if obj in self:
            return super().__getitem__(obj)
        elif match := [
            key for key in self if issubclass(obj, key) or isinstance(obj, key)
        ]:
            return super().__getitem__(match[0])
        raise KeyError("Patched object not found")


# dictionary of patched attributes. Access a patched attribute like so: patched[class][attribute_name]
patched = Patched()
