# This module defines a number of enumeration classes, characterized by:
# 1. A cardinality function card(n) for computing the number of values of size n
# 2. An indexing function index(n,i) for selecting a value of size n, giving a different values for each i < card(n)
#
# It is based on the Haskell library FEAT for enumerating algebraic datatypes:
# https://hackage.haskell.org/package/testing-feat
# If you make somthing useful from this, please let me know at jonas.duregard@chalmers.se

#import numpy
import json

"""
The enum type represents a sum (union) of a set of enumerations.
This is meant to represent an algebraic type.
Also applies a cost of one to elements (a.k.a. increases their size by 1)

Individual constructors are added after the object is created to enable recursive definitions. 
"""
class Enum:
  def __init__(self):
    self.constructors = []
    self.cards = [0] # for memoizing cardinalities

  """ c would typically be a Constructor object, but could be any enumeration """
  def addcon(self, c):
    self.constructors.append(c)
    self.cards = [0] # resets memoized cardinalities if there are any

  def card(self, n):
    if n<=0:
      return 0
    while(n >= len(self.cards)): # make sure the memoization table is large enough
      c = 0
      for con in self.constructors:
        c = c + con.card(len(self.cards)-1) # The -1 applies a cost
      self.cards.append(c)
    return self.cards[n]

  def index(self, n, i):
    for con in self.constructors:
      c = con.card(n-1)
      if i < c:
        return con.index(n-1, i)
      i = i - c
    cs = []
    raise ValueError("Size/index out of bounds")

"""
Enumeration that applies a function to a product of other enumerations.
Meant to represent a constructor of an algebraic type. 

For an N-ary function this uses O(N*s) memory where s is the maximum size used.
Time complexity of indexing is O(s) after some initial computations (that should be around N*s*s)
"""
class Constructor:
  def __init__(self, con, enums):
    if len(enums) == 0: # hack for nullary constructors
      self.card = lambda n: 1 if n==1 else 0
      self.index = lambda n,i: con()
    elif len(enums) == 1: # hack for arity-1 constructors
      self.card = lambda n: enums[0].card(n)
      self.index = lambda n,i:con(enums[0].index(n,i))
    else:
      self.con = con
      self.enums = enums
      self.next = 0 # The lowest undefined cardinality
      # The cardinality matrix, cs[k][n] is the nth cardinality of the product enums[k+]
      self.cs = [[] for e in enums] 
    
  def card(self,n):
    self.expand(n)
    return self.cs[0][n]

  def index(self, n, i):
    self.expand(n)
    args = [] # the actual values ('components') selected

    # select the first arity - 1 components
    for k in range(len(self.enums)-1):
      e = self.enums[k]
      esize = 0 # The size used for component k
      c = e.card(esize)*self.cs[k+1][n-esize]
      while i >= c: # linear search for the correct division of size
        i -= c
        esize += 1
        c = e.card(esize)*self.cs[k+1][n-esize]
      n -= esize
      # esize is now the size chosen for component k, n is the size remaining for all subsequent components
      (i,ei) = divmod(i, e.card(esize)) # split the index into a an index for compont k
      args.append(e.index(esize, ei))
    # Select the final component
    args.append(self.enums[-1].index(n, i))
    return self.con(*args)

  """ pre-compute cardinalities up to size n """
  def expand(self, n):
    arity = len(self.enums)
    while(self.next <= n):
      # the last column of cs is just the cardinality of enums[-1]
      self.cs[-1].append(self.enums[-1].card(self.next))

      # Fill in the rest of cs[k][self.next] in descending order of k
      # cs[k][n] is the sum of enums[k].card(n1)*cs[k+1][n2] for all n1+n2=n
      # each term of the sum represents one way of dividing size between the k'th component and all subsequent ones
      for k in range(len(self.enums)-2, -1, -1):
          c = 0
          for i in range(self.next+1):
            c = c + self.cs[k+1][i]*self.enums[k].card(self.next-i)
          self.cs[k].append(c)
      self.next = self.next+1
  
  #def dumpMatrix(self):
  #  print(numpy.matrix(self.cs))

""" Enumerates integers, defining the size of n to be n. """
class IntEnum:
  def card(self,n):
    return 1

  def index(self, n, i):
    return n

"""
Indexing function that doesn't take a size
Mostly included for fun. 
May fail to terminate for finite enumerations.
"""
def ix(enum, index):
  n = 0
  while(index > enum.card(n)):
    index = index - enum.card(n)
    n = n+1
  return enum.index(n,index)

""" prints all values of size n from enumeration e """
def all(e, n):
  for i in range(e.card(n)):
    print(e.index(n,i))

""" 'constructor' for lists. Mutates the original, but that's fine. I think. """
def app(x,xs):
  xs.append(x)
  return xs

""" 
Takes an enumeration and produces an enumeration of lists.
The size of a list is the number of elements + the combined size of elements + 1
"""
def elist(elems):
  e = Enum()
  e.addcon(Constructor(lambda: [], []))
  e.addcon(Constructor(app, [elems, e]))
  return e


# The rest of this file is an example: enumerating JSON-values

""" A slightly silly way to create a dictionary from a list of values"""
def listToMap(xs):
  res = {}
  key = 0
  for x in xs:
    res["a"+str(key)] = x
    key = key + 1
  return res

# An enumeration of a subset of JSON-values. 
ejson = Enum()
ejson.addcon(IntEnum()) # non-negative integers
ejsonarray = elist(ejson) 
ejson.addcon(ejsonarray) # JSON arrays
ejson.addcon(Constructor(listToMap, [ejsonarray])) # JSON objects where keys are always a0, a1, ...

print("prints all JSON-values of size 10")
all(Constructor(json.dumps, [ejson]),10)

print("\ncounts the number of JSON-values of size 200")
print(ejson.card(200))
print("selects one of those JSON-values and prints it")
print(json.dumps(ejson.index(200,1218021838232770697247976574152491929562517414831339501004063095)))


print("\nprints the 10^100th JSON-values in the enumeration order")
print(json.dumps(ix(ejson, 10**100)))



