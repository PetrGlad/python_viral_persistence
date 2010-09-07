Viral persistence for Python
----------------------------

User specifies a root object and all other objects that are transitively referenced by it's properties become persistent.
That means opjects to be persisted are not specified explicitly, this approach is similar to one of Smalltalk.

See main/Main.py for tests and usage examples.

How does it work
----------------

Changes to watched objects are detected via wrappers that serialize property changes into a log.
Any object that becomes referenced from already watched object is wrapped so further changes on it are also persisted.     
After system's restart it's state can be restored from log file.

Status
------

This is mostly a proof of concept and the implementation does  not handle collections properly (they are treated as atomic
objects).
    
Author Petr Gladkikh <PetrGlad@gmail.com>