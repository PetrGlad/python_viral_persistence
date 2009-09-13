# ---------------------------------------------------------
# Test code for persister

from StringIO import StringIO
from glight.core import SystemState, Updater, readInspect 

def dump(obj, indent=0):
    result = ''
    for name, value  in obj.__dict__.iteritems():
        result += " " * indent, name, "=", value 
    return result

def printChangeSet(gl):
    print 'Change set{'
    print ''.join(['\t' +  str(x) + '\n' for x in gl.changeSet]),
    print '}'

if __name__ == '__main__':
    class A(object):
        def __init__(self, other=None):
            self.name = 'eName'
            self.other = other
    class B(A):
        def __init__(self, other=None):
            A.__init__(self, other)
            self.bodd = 34
            self.hands = {"left":1}
    a = A()
    b = B(a)
    gl = SystemState(Updater)     
    b = gl.setRoot(b)
    b.hands["right"] = A()
    b.hands["right"].name = "rightHandObject"     
    roo = gl.root    
    roo.name = 'naMmm'
    MESSNAME = 'This is not lupus.'
    roo.name = MESSNAME 
        
    printChangeSet(gl)
    s = StringIO()
    gl.flush(s)
    
    b.hands["right"].other = b.hands["left"]
    printChangeSet(gl)
    gl.flush(s)
    
    s.seek(0)
    gl = SystemState(Updater)
    gl.load(s)
    assert gl.root.name == MESSNAME

    # begin: Test support for persistent lists
    #    assert gl.root.hands["left"] == 1
    #    assert gl.root.hands["right"].name == "rightHandObject"
    #    print gl.root.hands["right"].other # debug
    #    print gl.root.hands["left"] # debug
    #    assert gl.root.hands["right"].other == gl.root.hands["left"]
    # end

    MESSNAME2 = 'naMmm2'
    gl.root.name = MESSNAME2
    print '-- Objects --'
    print '\n'.join(['[' + str(id) + ']' + str(x) for id, x in gl.objects.iteritems()])
    print '-- Change set --'
    print '\n'.join([str(x) for x in gl.changeSet])
    
    gl.root.other = A()
    print '-- Change set --'
    print '\n'.join([str(x) for x in gl.changeSet])
    gl.flush(s)
    
    gl.root.other = A()
    NNAME = 'changedName'
    gl.root.other.name = NNAME 
    print '-- Change set --'
    print '\n'.join([str(x) for x in gl.changeSet])
    gl.flush(s)
    print '-- Change set --'
    # should be empty
    print '\n'.join([str(x) for x in gl.changeSet])
    
    print '-- What is stored --'
    s.seek(0)
    print "\n".join([str(x) for x in readInspect(s)])
    print '-- Loading back --'
    s.seek(0)
    gl = SystemState(Updater)
    gl.load(s)
    print 'other.name', gl.root.other.name
    assert NNAME == gl.root.other.name
    assert  MESSNAME2 == gl.root.name
