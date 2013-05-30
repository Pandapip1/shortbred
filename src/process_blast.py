#!/usr/bin/env python
#####################################################################################
#Copyright (C) <2013> Jim Kaminski and the Huttenhower Lab
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in the
#Software without restriction, including without limitation the rights to use, copy,
#modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
#and to permit persons to whom the Software is furnished to do so, subject to
#the following conditions:
#
#The above copyright notice and this permission notice shall be included in all copies
#or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# This file is a component of ShortBRED (Short, Better REad Database)
# authored by the Huttenhower lab at the Harvard School of Public Health
# (contact Jim Kaminski, jjk451@mail.harvard.edu).
#####################################################################################

import re
import sys
import csv
import argparse
import os
import subprocess
import glob
import math
import shutil

import Bio
from Bio import AlignIO
from Bio import Align
from Bio.Align import AlignInfo
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.Data import CodonTable
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

###############################################################################
def GetCDHitMap ( fileCluster, strTxtMap):
    setGenes = set()
    strFam = ""
    iLine = 0

    dictFams = {}

    for astrLine in csv.reader(open(fileCluster),delimiter='\t'):
		iLine+=1
		mtch = re.search(r'^>',astrLine[0])
		if (mtch):
		    if (len(setGenes)>0 and strFam!=""):
				for strGene in setGenes:
				    dictFams[strGene] = strFam
				setGenes=set()
				strFam = ""
		else:
		    mtchGene = re.search(r'>(.*)\.\.\.',str(astrLine[1]))
		    strGene = mtchGene.groups(1)[0]
		    setGenes.add(strGene.strip())
		    mtchFam = re.search(r'\.\.\.\s\*',str(astrLine[1]))
		    if mtchFam:
				strFam = strGene.strip()

    for strGene in setGenes:
				    dictFams[strGene.strip()] = strFam.strip()


    f = open(strTxtMap, 'w')
    for prot, fam in sorted(dictFams.items(), key = lambda(prot, fam): (fam,prot)):
		f.write(fam + "\t" + prot + "\n")
    f.close()

###############################################################################
def IsInHit( aiSeqQuery, aiSeqTarget):

	if (aiSeqQuery[0] >= aiSeqTarget[0] and aiSeqQuery[1] <= aiSeqTarget[1]):
		bInHit = True
	else:
		bInHit = False

	return bInHit

###############################################################################
def QMCheckShortRegion( setGenes, dictGenes, dictGOIHits,dictRefHits,iShortRegion=25,iMarkerLen=25):

	# This function takes a set of protein sequences that need QM's, and returns one
	# QM or nothing for each protein sequence.

	# For each seq, it looks at the first string of (iShortRegion) AA's. If that
	# region is not *completely* overlapped by any hit AND does not have more than one
	# "X", use that as a QM, and expand it until it is (iMarkerLen) AA's long.

	# If that region fails, slide down 1 amino acid, and look at the next set of
	# AA's. If function fails to find any candidate, return nothing for that seq.




	# Update this function to look in dictRefHits as well!

	atupQM = []


	for strGene in setGenes:
		# Initialize counters and bool values for loop
		iSeqLength = len(dictGenes[strGene])
		iStart = 1

		bHitEnd = False
		bFoundRegion = False
		bOverlapsSomeSeq = False

		atupHitInfo = dictGOIHits[strGene]

		# While the function has not found a QM, and has not hit the end of seq:
		#   Look at the section that is iShortRegion long.
		#   Check it against every hit in atupHitInfo.
		#   If it none of them completely overlap it, and
		while (bHitEnd == False and bFoundRegion == False):

			#Start from position 1, check if [1,iShortRegion] does not overlap with anything
			if ((iStart+iShortRegion-1) >= iSeqLength):
				bHitEnd = True

			bCheckedAllTup = False
			iTupCounter = 0
			while (bOverlapsSomeSeq == False and bCheckedAllTup == False and len(atupHitInfo)>0):
				tupHitInfo = atupHitInfo[iTupCounter]
				bOverlapsSomeSeq = IsInHit([iStart,iStart+iShortRegion-1],[tupHitInfo[1],tupHitInfo[2]])

				if(bOverlapsSomeSeq == False):
					strSeq = dictGenes[strGene][iStart-1:iShortRegion+(iStart-1)]
					if(strSeq.count("X")>1):
						bOverlapsSomeSeq = True
				iTupCounter+=1
				if(iTupCounter>=len(atupHitInfo)):
					bCheckedAllTup = True



			if(bOverlapsSomeSeq == False):
				# Found region, add amino acids to each side until you hit 20
				bFoundRegion = True
				iEnd = iStart + iShortRegion-1
				iLength = iEnd - iStart +1

				while iLength< iMarkerLen:
					if(iEnd<iSeqLength):
						iEnd+=1
						iLength = iEnd - iStart +1
					if(iLength < iMarkerLen and iStart>1):
							iStart = iStart-1
							iLength = iEnd - iStart +1

				tupQM = (strGene, dictGenes[strGene][iStart-1:iEnd],99, iStart,iEnd,[0,0,0,0,0])
				atupQM.append(tupQM)
			else:
				# Move the window up one space, try again
				iStart = iStart+1
                bOverlapsSomeSeq = False


	return atupQM









###############################################################################
def MakeFamilyFastaFiles ( strMapFile, fileFasta, dirOut):
#Makes a fasta file containing genes for each family in dictFams.
    dictFams = {}
    for strLine in csv.reader(open(strMapFile),delimiter='\t'):
		dictFams[strLine[1]]=strLine[0]


    dictgeneFamilies = {}

    for gene in SeqIO.parse(fileFasta, "fasta"):
		strFamily = dictFams.get(gene.id,"unassigned")
		aGene = dictgeneFamilies.get(strFamily,list())
		aGene.append(gene)
		dictgeneFamilies[strFamily] = aGene

    for key in dictgeneFamilies.keys():
		strFamFile = dirOut + os.sep + key +".faa"
		f = open(strFamFile, 'w')
		SeqIO.write(dictgeneFamilies[key], strFamFile, "fasta")
		f.close()

###############################################################################
def ClusterFams(dirClust, dCLustID, strOutputFile, dThresh):
#Clusters all of the family files made by MakeFamilyFastaFiles.

    dirFams = dirClust + os.sep + "fams"
    dirCentroids = dirFams+os.sep+"centroids"
    dirUC = dirFams+ os.sep + "uc"

    if not os.path.exists(dirClust):
		os.makedirs(dirClust)
    if not os.path.exists(dirFams):
		os.makedirs(dirFams)
    if not os.path.exists(dirCentroids):
		os.makedirs(dirCentroids)

    if not os.path.exists(dirUC):
		os.makedirs(dirUC)


    #sys.stderr.write( dirCentroids + "\n")
    #sys.stderr.write( str(glob.glob(dirFams+os.sep+'*.faa')) + "\n")
    for fileFasta in glob.glob(dirFams+os.sep+'*.faa'):
		#sys.stderr.write("The file is " + fileFasta + " \n")
		fileClust = dirCentroids + os.sep + os.path.basename(fileFasta)
		fileAlign = dirFams + os.sep + os.path.basename(fileFasta)+".aln"
		strSeqID = os.path.basename(fileFasta)
		strSeqID = strSeqID.replace(".faa", "")

		iSeqCount = 0
		#Count seqs, if more than one, then align them
		for seq in SeqIO.parse(fileFasta, "fasta"):
		    iSeqCount+=1


		if iSeqCount>1:
		    #Call muscle to produce an alignment
			subprocess.check_call(["muscle", "-in", str(fileFasta), "-out", str(fileAlign)])

            # Use BioPython's "dumb consensus" feature to get consensus sequence
			algnFasta = AlignIO.read(str(fileAlign), "fasta")

			seqConsensus =str(AlignInfo.SummaryInfo(algnFasta).dumb_consensus(threshold=dThresh, ambiguous='X'))
			seqConsensus = SeqRecord(Seq(seqConsensus),id=strSeqID)

			SeqIO.write(seqConsensus, str(fileClust), "fasta")


			"""
			# We previously used EMBOSS-CONS to produce consensus sequences
			# Call cons or em_cons from the EMBOSS package to produce a consensus sequence
			subprocess.check_call(["cons", "-seq", str(fileAlign), "-outseq", str(fileClust)])
			"""
		else:
		    shutil.copyfile(fileFasta,fileClust)



    ageneAllGenes = []

    for fileFasta in glob.glob(dirCentroids+os.sep+'*.faa'):
		for gene in SeqIO.parse(fileFasta, "fasta"):
		    gene.id = os.path.basename(os.path.splitext(fileFasta)[0])
		    ageneAllGenes.append(gene)

    """
    for gene in ageneAllGenes:
		mtch = re.search(r'centroid=(.*)',gene.id)
		if mtch:
		    gene.id = mtch.group(1)
		else:
		    gene.id = os.path.splitext()
    """

    SeqIO.write(ageneAllGenes, strOutputFile, "fasta")

###############################################################################
def printMap(strUCMap,strTxtMap):
#Converts usearch .uc file into two column (FamId, GeneId) file.

    dictGeneMap={}
    for strLine in csv.reader(open(strUCMap),delimiter='\t'):
		if (strLine[0] == "H"):
		    dictGeneMap[strLine[-2]] = strLine[-1]
		elif (strLine[0] == "C"):
		    dictGeneMap[strLine[-2]] = strLine[-2]

    f = open(strTxtMap, 'w')
    for prot, fam in sorted(dictGeneMap.items(), key = lambda(prot, fam): (fam,prot)):
		f.write(fam + "\t" + prot + "\n")
    f.close()

###############################################################################
def getGeneData ( fileFasta):
#Returns dict of form (GeneID, seq)
    dictGeneData = {}

    for gene in SeqIO.parse(fileFasta, "fasta"):
		    dictGeneData.setdefault(gene.id.strip(), str(gene.seq))


    if dictGeneData.has_key(''):
		del dictGeneData['']
    return dictGeneData

##############################################################################
def getOverlapCounts (fileBlast, dIDcutoff, iLengthMin, dLengthMax, iOffset, bSaveHitInfo):

# Makes a dictionary of form (GeneID, [0,0,0,0,1,1...]), where the number indicates
# the number of times an amino acid overlaps with a region in the blast output.

# PARAMETERS
# fileBlast - BLAST-formatted (fmt6) file of hits
# dIDcutoff - Minimum ID for using a hit
# iLengthMin - Lower bound for using a hit in AA's
# dLengthMax - Upper bound for using a hit (AlignmentLength/QueryLength)
# iOffset   - Number of AminoAcids at each end of valid hit which do NOT get +1 to their overlap counts
# bSaveHitInfo - When true, this records the name of the *Target* hit, and the start and end of the hit on the *Query*




#Read in the blast output line by line
#When the program finds a new QueryGene:
    #Add the last gene's aiCounts to dictAAOverlapCounts -- (gene, abWindow)
	#Add the last gene's atupHitInfo to dictOverlapInfo
    #Make a new aiCounts
#When the program finds the same QueryGene:
    #If the region in the blast hit satisfies our length and ID parameters
		#Set the corresponding location in abWindow equal to (count+1)

#Add the last gene when you finish the file

	strCurQuery = ""
	dictAAOverlapCounts = {}
	dictOverlapInfo = {}
	atupHitsInfo = []
	aiCounts =[]
	iGeneCount = 0
	iLine =0


    #sys.stderr.write("The file is " + fileBlast + "\n")
	for aLine in csv.reader( open(fileBlast, 'rb'), delimiter='\t' ):

		iLine+=1

		strQueryID = aLine[0]
		strSubId = aLine[1]
		dIdentity =float(aLine[2])/100
		iAln= int(aLine[3] )
		iMismatch = int(aLine[4])
		iGap = int(aLine[5] )
		iQStart = int(aLine[6] )
		iQEnd = int(aLine[7])
		iSubStart = int(aLine[8] )
		iSubEnd= int(aLine[9] )
		deVal = float(aLine[10] )
		dBit = float(aLine[11])
		iQLength = int(aLine[12])

		#When the current queryID changes, add the last one, and switch to the next gene.
		if strQueryID != strCurQuery:
			if iLine>1:
				dictAAOverlapCounts.setdefault(strCurQuery, aiCounts)
				dictOverlapInfo.setdefault(strCurQuery.strip(), atupHitsInfo)
			iGeneCount = iGeneCount+1
			strCurQuery = strQueryID

			atupHitsInfo = []
			aiCounts = []
			for i in range(iQLength):
				aiCounts.append(0)

		dMatchLength = (iAln) / float(iQLength)


		#If it's valid overlap:
		#   and 1 to each appopriate spot in the array
		#   save the name of the overlapping gene, and its start and end points
		#       Note: The latter region will include AA's outside what is marked as overlap, we still want that info.

		if (dIdentity >= dIDcutoff) and (iAln >=iLengthMin) and (dMatchLength <= dLengthMax) and (strQueryID!=strSubId):
			iOLCount = 0
			for i in range(iQStart-1+iOffset, iQEnd-iOffset):
				aiCounts[i]=aiCounts[i]+1
				iOLCount += 1
			if(bSaveHitInfo == True):
				tupInfo = strSubId, iQStart, iQEnd, iSubStart,iSubEnd, iOLCount
				atupHitsInfo.append(tupInfo)



	dictAAOverlapCounts.setdefault(strCurQuery.strip(), aiCounts)
 	dictOverlapInfo.setdefault(strCurQuery.strip(), atupHitsInfo)
  	iGeneCount = iGeneCount+1

	return dictAAOverlapCounts, dictOverlapInfo
	#tupAAandHits = (dictAAOverlapCounts, dictOverlapInfo)



###########################################################################
def MarkX(dictGenes, dictOverlap):

    for strName in dictGenes:
		for i in range(len(dictGenes[strName])):
		    if dictGenes[strName][i]=="X" or dictGenes[strName][i]=="x":
				dictOverlap[strName][i] = dictOverlap[strName][i] + 9999999

    return dictOverlap


###########################################################################
def CheckForMarkers(setGenes, dictKnockOut, iN):
#Take the genes in setNames, look in dictKnockOut (GeneID, [0,0,..])
#to see if they have a region of length N without any overlap.
# Returns set of genes (ID's) with markers.


    fFoundRegion = False
    fHitEnd = False
    iSumCounts = 0
    iMarkers = 0

    setGenesWithMarkers = set()

    for key in setGenes:
		aiWindow = dictKnockOut[key]
		iStart = 0
		while (fFoundRegion == False and fHitEnd == False):
		    if ((iStart+iN) > len(aiWindow)):
				fHitEnd = True
		    iSumCounts = sum(aiWindow[iStart:(iStart+iN)])
		    if (iSumCounts == 0 and fHitEnd==False):
				iMarkers +=1
				fFoundRegion = True
				setGenesWithMarkers.add(key)
		    iStart += 1
		fFoundRegion = False
		fHitEnd = False

    return setGenesWithMarkers
###############################################################################
def CheckForQuasiMarkers(setGenes, dictKnockOut, dictGenes, iN, iThresh, iTotLength):

    #Only run this on the leftover genes
    # "iN" = minimum window length
    #For each one, sum up the values from [0:n], then [1:n+1]...
    #Store these in an array of length (len(gene)-n)
    #Find the minimum value in this array
    #Take its index
    #Your window is [index:index+n]

    #Get the appropriate string from dictGOIgenes
    #add it to dictQM


    #Return dictQM with these windows

    #A QM_tuple has 4 values (name, markers, overlapvalue,iOriginalLength)


    atupQM = []



    for key in setGenes:
		aiWindow = dictKnockOut[key]



		import math

		#Take some function of each overlap count, reduce influence of outliers
		adAdjWindow = [math.pow(x,(1/4.0)) for x in aiWindow]

		iStart = 0
		dMin = 0
		dSumCounts = 0
		fHitEnd = False
		adWindowSums = []

		# Cycle through all windows of length N, record total overlap in aiWindowSums
		while (fHitEnd == False):
		    if ((iStart+iN) >= len(adAdjWindow)):
				fHitEnd = True
		    dSumCounts = sum(adAdjWindow[iStart:(iStart+iN)])
		    adWindowSums.append(dSumCounts)
		    iStart+=1

		# Find first AminoAcid of best window (lowest total overlap) with length N
		dMin = min(adWindowSums)
		iWinStart = adWindowSums.index(dMin)
		iWinEnd = iWinStart + iN

		bStop = False

		# Add next AA if that does not put this over the threshhold
		while(bStop==False and iWinEnd< len(dictGenes[key])-1 and len(adAdjWindow[iWinStart:iWinEnd+1]) < iTotLength):
		    if (sum(adAdjWindow[iWinStart:iWinEnd+1])<=iThresh):
				iWinEnd+=1
		    else:
				bStop=True

		#After you've grown the QM as much as possible to the right, try growing to the left.
		#Test the AA before the first AA of the QM, add it if it doesn't put you over iThresh
		while(bStop==False and iWinStart>= 1 and len(aiWindow[iWinStart-1:iWinEnd]) < iTotLength):
		    if (sum(adAdjWindow[iWinStart-1:iWinEnd])<=iThresh):
				iWinStart-=1
		    else:
				bStop=True


		iQuasi = int(sum(adAdjWindow[iWinStart:iWinEnd]))

		#Error Checking

		"""
		if key =="ZP_04318513":
			print "Data"
			print key
			print "Integer Window"
			print aiWindow
			print "Adjusted Window"
			print adAdjWindow
			print "Start,End",iWinStart, iWinEnd
			print adAdjWindow[iWinStart:iWinEnd]
			print dictGenes[key][iWinStart:iWinEnd]
			print "Quasi:",iQuasi
		"""


		tup = (key, dictGenes[key][iWinStart:iWinEnd],iQuasi, iWinStart,iWinEnd,aiWindow[iWinStart:iWinEnd])
		atupQM.append(tup)


		#Error Checking
		"""
		if (key == "VFG1266" or key == "VFG0696" or key=="VFG2059"):
		    print key
		    print dictRefCounts.get(key,"Not in Ref Blast Results")
		    print dictGOICounts.get(key,"Not in Clust Blast Results")
		    print dictGOIGenes[key]
		    print aiWindowSums

		    print iMin, iWinStart

		    print dictGenes[key][iWinStart:iWinStart+iN]
		"""
    return atupQM

######################################################################################
def GetQMOverlap(tupQM,atupHitInfo,fileOut,dictGOIGenes):
#   This function calculates the total amount of overlap between a QM and the ref
#   db or the clustered input seqs, depending on which atupHitInfo is entered.
#   It returns an integer with the total overlap, and outputs useful information
#   to fileOut (typically "QMtest.txt")

# 	Each QM has two atupHitInfo 's,  one from the goi-to-ref blast,
# 	and another from the goi-to-goi blast. They are made in the
# 	getOverlapCounts function and stored in dictionaries. (key=QM Seq Name)

# Give QM fields useful var names (examples in parentheses):
	strQMSeqName = tupQM[0]		# The seq for which the QM is built ("AAA25465")
	strQMSeqData = tupQM[1]     # ("RDRQGNIVDSLDSPRNKAPK")
	iQMOverlap = tupQM[2]       # Sum of Overlap, after ^(1/4) transformation ("28")
	iMarkerStart = tupQM[3]+1   # Start of QM Location on Seq, converted Python notation to BLAST. ("0" becomes "1")
	iMarkerEnd = tupQM[4]       # End of QM Location on Seq ("20")
	aiOverlapWindow = tupQM[5]	# Overlap window (*before* ^(1/4) transformation ("[5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 0]")

# Each a atupHitInfo contains tuples with the following six fields:
#   0 - Name of Overlapping/Target Seq
#   1 - Start of Overlap on Query Seq (All below in Blast format)
#   2 - End of Overlap on Query Seq
#   3 - Start of Overlap on Target Seq
#   4 - End of Overlap on Target Seq
#   5 - Overlap count

	iCounter = 1
	iTotalOverlap = 0 	#Sum of how much each sequence overlaps the QM (including the original prot)
	iCurOverlap = 0
	iCountOverlappingHits = 0


	# Print the QM AA's, add it to the overlap total
	fileOut.write(str(strQMSeqData) + '\n')
	iOriginalSeqOverlap = len(strQMSeqData)

	aaSeqOverlaps = []
	for tupHit in atupHitInfo:
		bOverlapsMarker = False
		strName = tupHit[0]

		# Overlap location on the marker (in Blast format)
		iOLMarkerStart = tupHit[1]
		iOLMarkerEnd = tupHit[2]

        # Overlap location on the hit (in Blast format)
		iOLHitStart = tupHit[3]
		iOLHitEnd = tupHit[4]

		iShift = iOLMarkerStart - iOLHitStart

		# If the hit is before or after the QM ...
		if (iOLMarkerStart > iMarkerEnd or iOLMarkerEnd < iMarkerStart):
			bOverlapsMarker = False

        # If the overlapping hit begins within the QM...
		elif (iMarkerStart <= iOLMarkerStart <= iMarkerEnd):
			iOLMarkerEnd = min(iMarkerEnd,iOLMarkerEnd)
			bOverlapsMarker = True

        # If the overlapping hit ends within the QM...
		elif(iMarkerStart <= iOLMarkerEnd <= iMarkerEnd):
			iOLMarkerStart = max(iMarkerStart,iOLMarkerStart)
			bOverlapsMarker = True

		# If the overlapping hit covers the marker, but doesn't begin or end in the marker, it *completely* overlaps it.
		else:
			iOLMarkerStart = iMarkerStart
			iOLMarkerEnd = iMarkerEnd
			bOverlapsMarker = True

		if (bOverlapsMarker==True):
			if(strName in dictGOIGenes.keys()):

				# The overlapping data from the Marker
				astrOverlapMarker = dictGOIGenes[tupQM[0]][(iMarkerStart):(iMarkerEnd)]

				# The overlapping data from the hit
				astrOverlap = dictGOIGenes[strName][(iOLMarkerStart-iShift-1):(iOLMarkerEnd-iShift)]

				astrOverlap = str("*"*(iOLMarkerStart - iMarkerStart)) + astrOverlap + str("*"*(iMarkerEnd- iOLMarkerEnd))


				# fileOut.write(astrOverlap + ' ' + strName + ' ' + str(iOLMarkerStart) +' '+str(iOLMarkerEnd) + ' '+str(iOLHitStart) + ' ' + str(iOLHitEnd) +' '+  str(tupHit[5]).zfill(3) + '\n')
				fileOut.write(astrOverlap + ' ' + strName + '\n')

			iSeqOverlap = iOLMarkerEnd-(iOLMarkerStart-1)
			iTotalOverlap+= iSeqOverlap
			iCountOverlappingHits +=1

			aSeqOverlap = [strName,iSeqOverlap]
			aaSeqOverlaps.append(aSeqOverlap)

	dOriginalSeqWeight = iOriginalSeqOverlap / float(iTotalOverlap + iOriginalSeqOverlap)

	fileOut.write( "Number of Overlapping Seqs: "+ str(iCountOverlappingHits) +'\n')
	fileOut.write( "Sum of Overlapping AA: "+ str(iTotalOverlap) +'\n')
	fileOut.write( "Original Sequence's Weight: "+ "{:3.2f}".format(dOriginalSeqWeight) +'\n' + '\n')

	return aaSeqOverlaps

####################################################################################


def UpdateQMHeader(atupQM,dictGOIHits,dictRefHits,strQMOut,dictGOIGenes,bUpdateHeader=False):
    #Each QM_tuple has the values: (name, window, overlapvalue,iMarkerStart,iMarkerEnd,aOverlap)



	atupUpdatedQM = []

	with open(strQMOut, 'w') as fQMOut:
		for tupQM in atupQM:
			strQMName = tupQM[0]
			strQMData = tupQM[1]
			iQuasi    = tupQM[2]
			aiOverlapWindow = tupQM[5]


			fQMOut.write("***********************************************************************" + '\n')

			# Write the QM out
			fQMOut.write(">" + strQMName + "_QM" + str(iQuasi) + "_#" + '\n')
			fQMOut.write(str(tupQM[1]) + '\n' + '\n')

			fQMOut.write("Overlap array for QM (before ^(1/4) transformation):" + '\n' + str(aiOverlapWindow) + '\n' + '\n')

			fQMOut.write("Overlap among GOI Seqs:" + '\n')
			aaGOIOverlap = GetQMOverlap(tupQM,dictGOIHits[strQMName],fQMOut,dictGOIGenes)
			fQMOut.write(str(aaGOIOverlap) + "\n")
			if(len(aaGOIOverlap)) > 0:
				iGOIOverlap = sum(zip(*aaGOIOverlap)[1])
			else:
				iGOIOverlap = 0

			if tupQM[0] in dictRefHits.keys():
				fQMOut.write("Overlap among Ref Seqs:" + '\n')
				aaRefOverlap = GetQMOverlap(tupQM,dictRefHits[strQMName],fQMOut,dictGOIGenes)
				if (len(aaRefOverlap)>0):
					iRefOverlap = sum(zip(*aaRefOverlap)[1])
				else:
					iRefOverlap = 0
				fQMOut.write(str(aaRefOverlap) + "\n")
			else:
				iRefOverlap = 0

			iAllOverlap =  iGOIOverlap + iRefOverlap + len(strQMData)

			astrNewHeader = []
			dPctOverlap =  len(strQMData) / float(iAllOverlap)
			astrNewHeader.append(strQMName + '_w=' + "{:0.3f}".format(dPctOverlap))

			for aLine in aaGOIOverlap:
				strName, iOverlap = aLine[0],aLine[1]
				dPctOverlap = iOverlap / float(iAllOverlap)
				strName = strName + '_w=' + "{:0.3f}".format(dPctOverlap)
				astrNewHeader.append(strName)

			strNewHeader = strQMName + "[" + ",".join(astrNewHeader) + "]"
			fQMOut.write(strNewHeader + '\n')

			dFinalWeight = len(strQMData) / float(iGOIOverlap + iRefOverlap + len(strQMData))
			strFinalWeight = "{:3.2f}".format(dFinalWeight)
			fQMOut.write("Final weight: " + strFinalWeight + '\n\n')
			aQM = [strQMName,strQMData,iQuasi,astrNewHeader]
			atupUpdatedQM.append(aQM)

	return atupUpdatedQM

###############################################################################
def PrintQuasiMarkers(atupQM, fileOut,bDetailed=False):
	iCounter = 0
 	strName = ""


	for tup in atupQM:
		if str(tup[0]) != strName:
			iCounter =1
		else:
			iCounter+=1
		if(bDetailed==True):
			fileOut.write(">" + str(tup[0]) + "_QM" + str(tup[2]) + "_#" +str(iCounter).zfill(2) + "__[" + ",".join(tup[3]) + "]" + '\n')
		else:
			fileOut.write(">" + str(tup[0]) + "_QM" + str(tup[2]) + "_#" +str(iCounter).zfill(2) + "_w" + '\n')
		fileOut.write(str(tup[1]) + '\n')
		#fileOut.write(str(tup))
		strName = str(tup[0])


	return

###############################################################################
##############################################################################
def CheckOutOfFrame (fileBlast, dIDcutoff, iWGSReadLen, dictFams, strOffTargetFile):

# Returns an set of Markers that may have result in out-of-frame alignments.
# This processes the blastx output, and flags the signficiant off-target
# matches from Markers (in nucs) to our GOI db (prots).

# Blastx alignment lengths are counted in *amino acids*. Query Lengths are given
# in *nucleotides*, so I divide by 3 to make them equivalent.

# "signficant off-target hit" = Any alignment with:
#	1) len>=min((querylength/3),iWGSReadLen) (32)
#   2) ID >= dIDcutoff (95%)
#   3) Target seq not in family of marker. (dictFams[target] != query)
#
# "32" comes from max Illumina read length in AA's. Maybe should be 33?


	astrProblemMarkers = []

	with open(strOffTargetFile, 'w') as fOut:
		csvOut = csv.writer(fOut, delimiter='\t', quoting=csv.QUOTE_NONE)
		for aLine in csv.reader( open(fileBlast, 'rb'), delimiter='\t' ):

			strQueryID = aLine[0]
			strSubID = aLine[1]
			dIdentity =float(aLine[2])/100
			iAln= int(aLine[3] )
			iMismatch = int(aLine[4])
			iGap = int(aLine[5] )
			iQStart = int(aLine[6] )
			iQEnd = int(aLine[7])
			iSubStart = int(aLine[8] )
			iSubEnd= int(aLine[9] )
			deVal = float(aLine[10] )
			dBit = float(aLine[11])
			iQLength = int(aLine[12])

			# Cut off the suffix on the markername
			# Ex: "ZP_01723236_TM_#02" --> "ZP_01723236"

			mtchProtStub = re.search(r'(.*)_(.M)[0-9]*_\#([0-9]*)',strQueryID)
			strMarkerProt = mtchProtStub.group(1)

			if (dIdentity >= dIDcutoff) and (iAln >= min((iQLength/3),iWGSReadLen)) and (dictFams[strSubID]!=strMarkerProt):
				csvOut.writerow(aLine)
				astrProblemMarkers.append(strQueryID)

	return set(astrProblemMarkers)


