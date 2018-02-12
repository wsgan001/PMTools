#Adapted from datasetGenerator.sh, just to generate more data for different theta_anomaly values, while fixing theta_trace to 0.5.

#Script for generating a dataset of models containing a range of anomalies (in quantity).

if [ $# -lt 1 ]; then
	echo "ERROR: Insufficient number of parameters $# passed to datasetGenerator.sh"
	exit
fi

rootFolder=$1
numActivities="30"
numTraces="1000"

logPath="testTraces.log"
syntheticGraphmlPath="syntheticModel.graphml"
modelPath="model.txt"

cd $rootFolder

modelCount=30
anomalyTheta=0.05
thetaTrace=0.50

for numAnomalies in {0,1,2,4,8,16}; do
	thisDir="A$numAnomalies"
	mkdir $thisDir
	cd $thisDir
	
	#make the logs at various theta-trace values, in increments of 0.2
	for numAnomalies in $(seq $modelCount); do
		echo making $logPath in $(pwd) and anomaly theta $anomalyTheta
		python ../../../ModelGenerator.py -n=$numActivities -a=$numAnomalies -config=anomalousModelExpt.config -file=$modelPath -graph=$graphmlPath -quiet --loopUntilKAnomalies
		#python ../../../DataGenerator/DataGenerator.py $syntheticGraphmlPath -n=$numTraces -ofile=$logPath --thetaAnomaly=$anomalyTheta --thetaTrace=$thetaTrace
	done

	cd ..
	pwd
done
