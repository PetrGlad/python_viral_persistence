import random

DISGITS63 = '0123456789abcdefghijklmnopqrstuvwxuzABCDEFGHIJKLMNOPQRSTUVWXUZ'
# DISGITS36 = '0123456789abcdefghijklmnopqrstuvwxuz'

def makeId():
    return ''.join([random.choice(DISGITS63) for _ in range(10)])

def getId(obj):
    if not hasattr(obj, 'id'):
        obj.__dict__['id'] = makeId()
    return obj.id
