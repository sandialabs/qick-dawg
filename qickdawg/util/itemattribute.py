"""
ItemAttribute
=================================================
Class that allows access to attributes like a standard class
but also allows access to attributes with dictionary item syntax

i.e. "attribute" of "class" can be accessed as
class.attribute 

or 

class["attribute"]

"""


class ItemAttribute(object):
    '''
    Class that has propertys which can be called like dictionary
    items

    Args:
        dictionary - (default None) dictionary object
    '''


    def __init__(self,dictionary=None):
        if dictionary!=None:
            for k in dictionary.keys():
                self[k]=dictionary[k]

    __getitem__ = object.__getattribute__
    __setitem__ = object.__setattr__
    __delitem__ = object.__delattr__

    def __contains__(self, item):
        return item in self.__dict__

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()
