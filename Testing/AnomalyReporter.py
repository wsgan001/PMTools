"""
Given the output of gbad containing found-anomalies, and the original trace log containing
+/- anomaly labelings, this object compares the two and generates the matrix for
true positives, false positives, true negatives, and false negatives.

The gbad output may contain output of any gbad version (mdl, mps, prob), and output of each gbad
version can be concatenated into a single file as input to this script. Mdl and mps output is the same,
but the fsm version declares anomalies slightly differently. All are plaintext files, which ought to be
updated to something more rigorous. This doesn't handle fsm output directly, but can with a little
preprocessing: grep "transaction containing anomalous structure" $fsmResult | uniq | sort > $fsmTemp

The info is just printed to the output, but keep it parseable if possible.
"""
from __future__ import print_function
import sys
from Dendrogram import *

class AnomalyReporter(object):
	def __init__(self, gbadPath, logPath, resultPath, dendrogramPath=None, dendrogramThreshold=0.05):
		self._gbadPath = gbadPath
		self._logPath = logPath
		self._resultPath = resultPath
		self._dendrogramPath = dendrogramPath
		self._dendrogramThreshold = dendrogramThreshold

	"""
	Given a file containing gad output, parses the text for all of the anomalies detected. Each
	anomaly must contain the corresponding trace number associated with a trace in the original
	log file (labelled +/- for anomaly status).
	
	Returns: A list of integers that are the ids of any 
	"""
	def _parseGbadAnomalies(self, gbadFile):
		self._detectedAnomalyIds = []
		gbadOutput = gbadFile.readlines()
		#print("output: "+gbadOutput)
		gbadFile.close()

		"""
		Gbad output (in the versions I've used) always has anomalies anchored with the file-unique string
		"from example xx" where xx is the integer number of the anomalous graph, the same as the trace id in the trace log.
		Thus, search for all lines with this string, parse the number, and we've a list of trace-ids for the anomalies.
		"""
		for line in gbadOutput:
			#detects gbad-mdl, -mps, -prob anomal declarations (mdl/mps use "from example", gbad-prob uses "from positive example")
			if "from example " in line:
					#print("found anom: "+line)
					#parses 50 from 'from example 50:'
					id = int(line.strip().split("from example ")[1].replace(":",""))
					self._detectedAnomalyIds.append(id)
			#detects gbad-prob anomalous subgraph example declarations
			if "in original example " in line:
					#print("found anom: "+line)
					#parses 50 from 'in original example 50)'
					id = int(line.strip().split("in original example ")[1].replace(")",""))
					self._detectedAnomalyIds.append(id)

			#detects output format of gbad-fsm
			if "transaction containing anomalous structure:" in line:
				id = int(line.split("structure:")[1].strip())
				self._detectedAnomalyIds.append(id)
				
	"""
	Parses a trace log file into the object's internal storage. These are the ground truth anomalies, not those detected by gbad.
	
	@self._anomalies: a list of anomalous traces (tokenized by comma)
	"""
	def _parseLogAnomalies(self,logFile):
		#maintain traces internally as a list of <traceNo,+/-,trace> string 3-ples
		self._logTraces = [trace.split(",") for trace in logFile.readlines() if len(trace.strip()) > 0]
		#get the subset of the traces which are anomalies
		self._logAnomalies = [trace for trace in self._logTraces if trace[1] == "+"]
		#get the non-anomalies
		self._logNegatives = [trace for trace in self._logTraces if trace[1] == "-"]
		logFile.close()
		
	"""
	Given a float in range 0.0 to 1.0, such as 0.4567532, returns "45.67%" (hundredths precision)
	"""
	def _floatToPctStr(self, f):
		return str(float(int(f * 10000)) / 100.0)+"%"

	"""
	Keep this clean and easy to parse.
	"""
	def _displayResults(self):	
		output = "Statistics for log parsed from "+self._logPath+", anomalies detected\n"
		#output += "True positives:  \t"+str(len(self._truePositives))+"\t"+str(self._truePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"

		output += ("Num traces (N): \t"+str(self._numTraces)+"\n")
		output += ("Accuracy:          \t"+str(self._accuracy)+"  ("+self._floatToPctStr(self._accuracy)+")\n")
		output += ("Error rate:         \t"+str(self._errorRate)+"  ("+self._floatToPctStr(self._errorRate)+")\n")
		output += ("Recall:              \t"+str(self._recall)+"  ("+self._floatToPctStr(self._recall)+")\n")
		output += ("Precision:          \t"+str(self._precision)+"  ("+self._floatToPctStr(self._precision)+")\n")
		
		output += ("True positives:   \t"+str(len(self._truePositives))+"\t"+str(self._truePositives)+"\n")
		output += ("False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives)+"\n") 
		output += ("True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives)+"\n")
		output += ("False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives)+"\n")

		print(output)
		
		ofile = open(self._resultPath, "w+")
		ofile.write(output)
		ofile.close()

	"""
	Gbad doesn't always report all instances of a given anomaly; so if "ABC" is reported as an 
	anomaly, it doesn't always report all "ABC" traces as anomalies in it results. 
	
	NOTE: I've only currently written this to look for traces (strings) in the trace file which are
	matching strings. This covers 99% of the cases, however, traces like "ACB" could theoretically
	be included and NOT caught as equivalent to some found-anomaly "ABC". THIS NEEDS TO BE FIXED.
	That is, for each anomaly, we need to reconstruct it graphically according to the mined model, then compare 
	the anomaly to all other traces as graphs.
	
	@anoms: list of anomalies as a list of 3-ples: string-id (the first field of each trace in logTraces), +/-, and traceStr
	
	returns: Full list of anomalous traces as 3-ples.
	"""
	def _unifyAnomalies(self):
		#print("detected: "+str(set(self._detectedAnomalyIds)))
		#print("traces: "+str(self._logTraces))
		anoms = []
		#get the anomaly list as a list of 3-ples
		for id in set(self._detectedAnomalyIds):
			for trace in self._logTraces:
				if trace[0] == str(id):
					anoms.append(trace)
	
		ids = set([a[0] for a in anoms])
		equivalentAnoms = []
		#given each anomaly, look for others with the same trace-string which are not yet included in the anomaly set
		for anom in anoms:
			id = anom[0]
			traceStr = anom[2]
			#search for other log-traces with this same trace-string. This is an insufficient match, since these are technically graphs.
			for logTrace in self._logTraces:
				#if logTrace[2] == traceStr:
				#	print("traceStr hit"+str(logTrace))#+"  ids: "+str(ids))
				if logTrace[2] == traceStr and logTrace[0] not in ids:
					#print("Extra anomaly detected for "+traceStr+" "+id+": "+logTrace[0])
					equivalentAnoms.append(logTrace)
					ids.add(logTrace[0])
		
		anoms += equivalentAnoms
					
		#print("all anoms: "+str(anoms))
		return anoms

	
		
		
	"""
	TODO: Dendrogram could certainly be its own class at some point; this is fine for now.
	
	A dendrogram is as demonstrated in dendrogram.txt. The intent is for the Dendrogram object
	to support querying, such as "given this anomalous/outlier trace, what is the nearest compressing substructure?"
	
	returns: The dendrogram, which is just an ordered list of compression levels, with the last/bottom-most at back
	"""
	def _buildDendrogram(self, path):
		anomalyIds = []
		dendrogram = []
		f = open(self._dendrogramPath,"r")
		
		#build the compression levels, each of which is an object with compressed id's, max compressed id's, compression factor (from gbad), num instances, etc
		for line in f.readlines():
			if len(line.strip()) > 0:
				cl = CompressionLevel(line.strip())
				dendrogram.append(cl)
		
		return dendrogram
		
	"""
	For experimentation: search for metrics that distinguish outliers from anomalies, where loosely speaking, anomalies occur in the context of some
	sort of "normal" behavior. Think of having to identify anomalies using no threshold in terms of the size-reduction of compression levels.
	
	@dendrogram: Simply a list of CompressionLevels, with the last item representing the lowest trace/subs in the dendrogram
	"""
	def _analyzeDendrogram(self, dendrogram):
		threshold = 0.15
		numTraces = float(len(dendrogram[0].IdMap.keys()))
		#for now, just look at the least 10% or so of compressing traces, without parsing trace-graphs for graph comparison
		candidateIndex = -1 #the index in the compression level list (dendrogram) at which the number of ids drops below threshold in terms of frequency
		i = 0
		while i <  len(dendrogram):
			level = dendrogram[i]
			if (float(len(level.IdMap.keys())) / numTraces) <= threshold:
				candidateIndex = i
				break
			i += 1

		#now build the ancestry dict, mapping each id in the anomaly set to a tuple containing a list of compressing substructure ids higher in the hierarchy, and the cumulative compression value
		ancestryDict = {}
		candidateLevel = dendrogram[candidateIndex]
		candidateIds = candidateLevel.IdMap.keys()
		#for each id among the candidates (outliers and anomalies), show their ancestry, rather their derivation in the dendrogram, if any
		print("candidate ids: "+str(sorted(candidateIds))+" for threshold "+str(threshold))
		for id in candidateIds:
			#backtrack through the layers, showing the ancestry of this id, along with compression stats
			ancestry = [] #tuples of the form (SUB:numInstances:compFactor)
			cumulativeCompression = 0.0
			i = candidateIndex - 1
			curId = id #watch your py shallow copy...
			while i >= 0:
				curLevel = dendrogram[i]
				#print("level: "+curLevel.Line)
				curId = curLevel.ReverseIdMap[curId]
				#check if id was in the compressed set on this iteration/level; if so, append it to ancestry with other statistical measures
				if curId in curLevel.CompressedIds:
					#calculate KL div
					
					ancestry.append(i)
					cumulativeCompression += curLevel.CompressionFactor
				i -= 1
			#all (if any) ancestor level-indices appended to ancestry, so just add this list for this id
			ancestryDict[curId] = (ancestry,cumulativeCompression)

		#print, just to observe traits of anomalies
		print("Candidate-id Ancestry")
		print(str([(str(k),ancestryDict[str(k)]) for k in sorted([int(sk) for sk in ancestryDict.keys()])]))

		
		
		
	#Just a wrapper for building and then analyzing the dendrogram, for research
	def _dendrogramAnalysis(self, path):
		dendrogram = self._buildDendrogram(path)
		self._analyzeDendrogram(dendrogram)
	
	"""
	For now, this is without much nuance. Given a dendrogram, backtrack until the size of the trace subset is > 5%
	of the overall size of the traces.
	@threshold: The dendrogram threshold; about 0.05 is about right
	"""
	def _compileDendrogramResult(self, threshold):
		anomalyIds = []
		compressionLevels = []
		f = open(self._dendrogramPath,"r")
		#parse the dendrogram file; the only important component is backtracking the trace-ids to their original ids
		for line in f.readlines():
			idMappings = line.split("{")[1].split("}")[0].split(",")
			newMap = {}
			for mapping in idMappings:
				prevId = mapping.split(":")[0]
				nextId = mapping.split(":")[1]
				newMap[prevId] = nextId
			compressionLevels.append(newMap)

		#print(str(compressionLevels))
		#get the total number of traces from the size of the first id-map
		numTraces = len(compressionLevels[0].keys())
		#march forward in compression levels until we reach the subset of traces whose size is less than some anomalousness threshold;
		#all these traces are anomalies. Once we have them, backtrack to their original id's.
		i = 0
		while i < len(compressionLevels) and float(len(compressionLevels[i])) / float(numTraces) > threshold:
			print("ratio: "+str(float(len(compressionLevels[i])) / float(numTraces)))
			i += 1
		print("i = "+str(i)+" numTraces="+str(numTraces))
		#check if anomalous group found; if so, backtrack to get their original ids
		if i > -1 and i < len(compressionLevels):
			#backtrack to the original ids; the keys in each level are the vals of the previous level
			prev = i - 1
			curKeys = compressionLevels[i].keys()
			print(str(curKeys))
			while prev >= 0:
				#print("curKeys: "+str(compressionLevels[i].keys()))
				#print("prev items: "+str(compressionLevels[prev].items()))
				#print("cur keys: "+str(compressionLevels[i].items()))

				prevKeys = []
				for k in curKeys:
					prevKeys += [pair[0] for pair in compressionLevels[prev].items() if pair[1] == k]
				#print("PKEYS: "+str(prevKeys))
				curKeys = [k for k in prevKeys]
				"""
				curKeys = []
				for pair in compressionLevels[prev].items():
					for k in compressionLevels[i].keys():
						if pair[1] == k:
							curKeys.append(pair[0])
				"""
				#curKeys = [pair[0] for pair in compressionLevels[prev].items() if pair[1] in compressionLevels[i].keys()]
				prev -= 1
				#i -= 1

			print("Dendrogram-based anomalies: ")
			curKeys = [int(k) for k in curKeys]
			curKeys = sorted(curKeys)
			print(str(curKeys))
			anomalyIds = curKeys
		else:
			print("Dendrogram-based anomalies:  >>no anomalies found<<")

		#report confusion matrix, other values
		self._outputResults(anomalyIds)


	"""
	Opens traces and gbad output, parses the anomalies and other data from them, necessary
	to compute false/true positives/negatives and then output them to file.
	"""
	def CompileResults(self):
		#compile and report the dendrogram results separately; this is sufficient for determining if the dendrogram-based methods even work
		if self._dendrogramPath != None:
			self._dendrogramAnalysis(self._dendrogramPath)
			self._compileDendrogramResult(self._dendrogramThreshold)

		#soon to be dead code: report recursive-gbad results
		self._reportRecursiveAnomalies()
		
		print("Result Reporter completed.")

	"""
	Feed this only a list of integer anomaly id's, and it automatically generates the confusion values,
	and displays the results

	@anomalies: a list of integer anomaly id's
	"""
	def _outputResults(self, anomalies):
		logFile = open(self._logPath, "r")
		self._parseLogAnomalies(logFile)
		self._detectedAnomalyIds = anomalies
		
		#create the true anomaly and detected anomaly sets via the trace-id numbers
		truePositiveSet = set( [int(anomaly[0]) for anomaly in self._logAnomalies] )
		trueNegativeSet = set( [int(anomaly[0]) for anomaly in self._logNegatives] )
		detectedAnomalies = set(self._detectedAnomalyIds)

		#store overall stats and counts
		self._numDetectedAnomalies = detectedAnomalies
		self._numTraces = len(self._logTraces)
		self._numTrueAnomalies = len(self._logAnomalies)

		#get the false/true positives/negatives using set arithmetic
		self._truePositives = detectedAnomalies & truePositiveSet
		self._falsePositives = detectedAnomalies - truePositiveSet
		self._trueNegatives = trueNegativeSet - detectedAnomalies
		self._falseNegatives = truePositiveSet - detectedAnomalies

		#compile other accuracy stats
		self._errorRate = float(len(self._falseNegatives) + len(self._falsePositives)) / float(self._numTraces) #error rate = (FP + FN) / N = 1 - accuracy
		self._accuracy =  float(len(self._trueNegatives) + len(self._truePositives)) / float(self._numTraces) # accuracy = (TN + TP) / N = 1 - error rate

		#calculate precision: TP / (FP + TP)
		denom = float(len(self._falsePositives) + len(self._truePositives))
		if denom > 0.0:
			self._precision =  float(len(self._truePositives)) / denom
		else:
			self._precision = 0.0
		
		#calculate recall: TP / (TP + FN)
		denom = float(len(self._truePositives) + len(self._falseNegatives))
		if denom > 0.0:
			self._recall = float(len(self._truePositives)) / denom
		else:
			self._recall = 0.0
		
		#convert all sets to sorted lists
		self._truePositives = sorted(list(self._truePositives))
		self._falsePositives = sorted(list(self._falsePositives))
		self._trueNegatives = sorted(list(self._trueNegatives))
		self._falseNegatives = sorted(list(self._falseNegatives))

		self._displayResults()

	"""
	This may soon be dead code, based on better results with the delete-sub method:
	outputs anomalies found by recursive gbad, by which gbad is re-run on compressed
	subs.
	"""
	def _reportRecursiveAnomalies(self, ):
		gbadFile = open(self._gbadPath, "r")

		self._parseGbadAnomalies(gbadFile)
		#gbad doesn't always report all equivalent anomalies; this simply unifies all reported anomalies with traces that are the same
		self._detectedAnomalyIds = [int(trace[0]) for trace in self._unifyAnomalies()]
		self._outputResults(self._detectedAnomalyIds)
		
def usage():
	print("Usage: python ./AnomalyReporter.py -gbadResultFiles=[path to gbad output] -logFile=[path to log file containing anomaly labellings] -resultFile=[result output path] [optional: --dendrogram=dendrogramFilePath --dendrogramThreshold=[0.0-1.0]")
	print("To get this class to evaluate multiple gbad result files at once, just cat the files into a single file and pass that file.")

"""

"""
def main():
	if len(sys.argv) < 4:
		print("ERROR incorrect num args")
		usage()
		exit()

	gbadPath = sys.argv[1].split("=")[1]
	logPath = sys.argv[2].split("=")[1]
	resultPath = sys.argv[3].split("=")[1]
	dendrogramPath=None
	if len(sys.argv) >= 5 and "--dendrogram=" in sys.argv[4]:
		dendrogramPath = sys.argv[4].split("=")[1]
	
	dendrogramThreshold = 0.05
	if len(sys.argv) >= 6 and "--dendrogramThreshold" in sys.argv[5]:
		dendrogramThreshold = float(sys.argv[5].split("=")[1])
	
	reporter = AnomalyReporter(gbadPath, logPath, resultPath, dendrogramPath, dendrogramThreshold)
	reporter.CompileResults()

if __name__ == "__main__":
	main()



