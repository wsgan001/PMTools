
"""
Simple class comprising the information in a single compression level, as shown in a line in dendrogram.txt.

All id's are maintained as strings.
"""
class CompressionLevel(object):
	def __init__(self, line):
		self.Initialize(line)

    """
    Takes the grpah portion of the dendrogram (a python list of vertex name pair tuples) and convert to an igraph
    """
    def _getSubGraph(self, line):
        edgeList = eval(line)
        
        vs = set()
        for edge in edgeList:
            vs.add(edge[0])
            vs.add(edge[1])
        
        g = igraph.Graph(directed=True)
        g.add_vertices(vs)
        g.add_edges(edgeList)
        
        return g
        
	"""
	Given a line in a dendrogram file, fills in all data for this compression level
	
	@line: a line like "([1,3,4]1,2,3,4:SUB7:4:2.24336)7,8,9{2:1,1:-1,3:-1,4:-1}#[('a','b'),('c','b')...]"
	"""
	def Initialize(self,line):
		#print("line: >"+line+"<")
        graphLine = line.split("#")[1]
        line = line.split("#")[0]
        
        self.SubGraph = self._getSubGraph(line.split("#")[1])
		self.MaxCompressedIds = [id for id in line.split("[")[1].split("]")[0].split(",") if len(id) > 0] #magic prevents empty max-comp list '[]' from becoming [''] (one item list of empty str)
		self.CompressedIds = line.split("]")[1].split(":")[0].split(",")
		self.UncompressedIds = [id for id in line.split(")")[1].split("{")[0].split(",") if len(id) > 0]
		self.NumInstances = int(line.split(")")[0].split(":")[-2])
		self.CompressionFactor = float(line.split(")")[0].split(":")[-1])
		self.SubName = line.split(")")[0].split(":")[-3]
		self.Line = line.strip()
		
		#initialize the id-map: the left id is for the current compression level; right id's mapping to -1 are traces that reached maximum compression
		self.IdMap = {}
		self.ReverseIdMap = {} #maps ids in reverse: successors are keys, predecessor ids are values
		idPairs = line.split("{")[1].split("}")[0].split(",") #from {2:1,1:-1,3:-1,4:-1} gets list: ["2:1","1:-1"...]
		for pair in idPairs:
			leftId = pair.split(":")[0]
			rightId = pair.split(":")[1]
			self.IdMap[leftId] = rightId
			#reverse map will include only non-negative values
			if rightId != "-1":
				self.ReverseIdMap[rightId] = leftId
		
		"""
		print("max comps: "+str(self.MaxCompressedIds))
		print("comp ids: "+str(self.CompressedIds))
		print("uncomp ids: "+str(self.UncompressedIds))
		print("num instances "+str(self.NumInstances))
		print("compfact: "+str(self.CompressionFactor))
		print("idmap: "+str(self.IdMap))
		"""
		
		