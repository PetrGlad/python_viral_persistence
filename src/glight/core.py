"""
    Viral persistence layer: user specifies a root object and 
    all other objects that are transitively referenced by it's
    properties become persistent.
    Changes to watched objects are detected via wrappers 
    that serialize property changes into a log. Any object
    that becomes referenced from already watched object is
    wrapped so further changes on it are also persisted.     
    After system's restart it's state can be restored from log file.
    
    This is mostly a proof of concept and the implementation does
    not handle collections properly (they are treated as atomic
    objects) and there can be also remaining holes to plug.
    
    See main/Main.py for tests and usage examples.
     
    Author: Petr Gladkikh <PetrGlad@gmail.com>
"""

import pickle
from glight.util import getId


class Thunk(object):
    """Field value: persistent reference to a composite object.
    Represents field object that refers to other composite (is object reference)"""
    
    def __init__(self, objectId):        
        self.objectId = objectId # parent object this field attached to    
        
    def __str__(self):
        return 'ref(' + self.objectId + ')'
    
    def resolve(self, ctx): 
        """
        Resolve reference (represented by 'self' object) to actual object. 
        Lazy resolution is essential as there can be circular references.
        """
        return ctx.objects[self.objectId]


class Record(object):
    def __init__(self, id):         
        self.id = id # object or item id

    def __str__(self):
        return 'id=' + self.id


class Composite(Record):
    def __init__(self, id, classRef):
        Record.__init__(self, id)
        self.classRef = classRef
        
    def putInPlace(self, context, wrapper):
        obj = self.classRef()
        obj.id = self.id
        context[self.id] = wrapper(obj)
        
    def __str__(self):
        return 'C, ' + Record.__str__(self) + ', class=' + str(self.classRef)

        
class Field(Record):
    def __init__(self, parentId, attrName, value):
        Record.__init__(self, parentId + '.' + attrName)
        self.parentId = parentId
        self.attrName = attrName # attribute of aggregating object
        self.value = value
        
    def putInPlace(self, context, wrapper):
        context[self.parentId].__dict__[self.attrName] = wrapper(self.value)
        
    def __str__(self):
        # parent can be seen as part of id
        return 'F, ' + Record.__str__(self)\
            + ', \'' + self.attrName + '\'=' + str(self.value)        


def isAtomic(obj):
    "Return true if object be stored as whole (is not split into fields)"
    # TODO we probably should trait collections separately
    return type(obj) in [type(None), dict, list, tuple, str, int, long, complex, float]    

    
def write(stream, obj):
    def dump(value): pickle.dump(value, stream, pickle.HIGHEST_PROTOCOL)
    dump(Composite(getId(obj), obj.__class__))
    for fieldName, fieldValue in obj.__dict__.iteritems():
        if isAtomic(fieldValue):
            dump(Field(obj.id, fieldName, fieldValue))            
        else:            
            dump(Field(obj.id, fieldName, Thunk(getId(fieldValue))))
            write(stream, fieldValue)


def readInspect(stream):
    "Load contents of log without any processing. Is used for debugging purposes)"
    records = []
    try:
        while True:
            records.append(pickle.load(stream))
    except EOFError:
        return records

class Root(object):
    "Class of object hierarchy root. (Used by SystemState class)."
    ID = "root"
    def __init__(self):
        self.id = Root.ID


class SystemState:
    "Persistent context of user objects."
    
    def __init__(self, updaterClass):
        # true if system state is currently being restored from logs
        self.loadMode = False
        
        # object id -> object map        
        self.objects = {}
        
        # pending changes to be written to the log
        self.changeSet = []
        
        # class of object wrappers
        self.updaterClass = updaterClass
        
    def resetRoot(self):
        roo = self.updaterClass(Root(), self)
        roo.putInPlace()
        
    def updateItem(self, obj, index, value):
        if not self.loadMode:
            print 'upd ' + `obj` + '[' + `index` + '] <--' + `value` # DEBUG
            if isAtomic(value):
                self.changeSet.append(Field(getId(obj), index, value))            
            else:
                self.changeSet.append(Field(getId(obj), index, Thunk(value.id)))
        
    def add(self, obj):
        """
        Make given object persistent (along with objects it refers recursively).
        Add it to objects map and add to changeset.
        
        We should use only on-demand adopting as eager recursive adoption won't 
        help if something external holds reference to inner object. Furthermore 
        lazy adoption only in Updater objects will simplify code somehow.  
        """
        if not self.loadMode:
            if getId(obj) in self.objects:
                raise Exception("Object with id " + getId(obj) + " is already registered")
            else:
                self.changeSet.append(Composite(getId(obj), type(obj)))
        self.objects[obj.id] = obj                

    def flush(self, stream):
        for value in self.changeSet:
            pickle.dump(value, stream, pickle.HIGHEST_PROTOCOL)
        self.changeSet = []    
        
    def load(self, stream):
        # Note that the function is not thread safe, should be executed exclusively
        self.loadMode = True
        try:
            def wrap(x):
                if type(x) != Thunk:
                    return x
                else:
                    return self.updaterClass(x.resolve(self), self)
            try:
                while True:
                    record = pickle.load(stream)
                    # print 'loaded record ' + str(record) # DEBUG
                    record.putInPlace(self.objects, wrap)    
            except EOFError:
                pass
            self.setRoot(self.objects[Root.ID])
        finally:
            self.loadMode = False
  
#    def __getattr__(self, attrName):
#        if 'root' == attrName:             
#            return self.root
#        else:
#            raise AttributeError(attrName)
    
    def setRoot(self, root):
        assert not isAtomic(root)
        root.__dict__['id'] = Root.ID # XXX I am sure there are better solutions.           
        self.__dict__[Root.ID] = self.updaterClass(root, self)
        return self.root
        
class Updater(object):
    """Wrapper that allows watching attribute changes. It is run-time object 
    and should not be persisted.
    
    TODO How do we handle collections? represent index as field name?
    """
    
    # Used to disambiguate glight auxiliary attributes from user ones
    SPECIAL_ATTR_PREFIX = 'glight'
    
    # Name of attribute that holds actual user object 
    OBJ_ATTR = SPECIAL_ATTR_PREFIX + '_obj'
    
    # Name of attribute that holds persistent context
    CTX_ATTR = SPECIAL_ATTR_PREFIX + '_ctx'
    
    # This is wrappers cache. Allows to create only one wrapper per object instance 
    wrappers = {}
        
    def __init__(self, obj, ctx):
        # __dict__ is used to detour getattr and setattr  
        self.__dict__[self.OBJ_ATTR] = obj
        self.__dict__[self.CTX_ATTR] = ctx
        ctx.add(obj)
        print obj.__dict__ # DEBUG
        for attrName, attrValue in obj.__dict__.iteritems():
            if not attrName.startswith(self.SPECIAL_ATTR_PREFIX):            
                setattr(self, attrName, attrValue) # Calls self.__setattr__                

    def __setattr__(self, attrName, value):
        """ Set attribute on enclosed object.
        """        
        self.updatePart(attrName, value)

    def __setitem__(self, index, value):
        self.updatePart(index, value)
        self.__dict__[self.OBJ_ATTR].__setitem__(index, value)        
        
    def updatePart(self, attrName, value):
        if isAtomic(value):
            attrValue = value
        else:
            attrValue = self.getWrapped(value)
        setattr(self.__dict__[self.OBJ_ATTR], attrName, attrValue)
        self.__dict__[self.CTX_ATTR].updateItem(self.__dict__[self.OBJ_ATTR], attrName, value)
        
    def __getattr__(self, attrName):
        """Get attribute of enclosed object."""        
        return self.__dict__[self.OBJ_ATTR].__dict__[attrName]
        
    def getWrapped(self, object):
        """Get wrapped composite and cache wrapper."""
        id = getId(object)
        if id in self.wrappers:
            return self.wrappers[id]
        else:
            wrapped = self.__class__(object, self.__dict__[self.CTX_ATTR])
            self.wrappers[id] = wrapped
            return wrapped
    
    def __getstate__(self):
        raise Exception(self.__class__.__name__ + " is not serializable.")

    def __str__(self):
        return 'Updater{' + `self.__dict__[self.CTX_ATTR]` + ', ' + `self.__dict__[self.OBJ_ATTR]` + '}'
