#!/usr/bin/python



import Bio
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.Data import CodonTable
from Bio import SeqIO

#test for Nicola
from collections import OrderedDict
#from collections import defaultdict



import re
import sys
import argparse


parser = argparse.ArgumentParser(description='Compares file of windows against orginial, clustered file to count windows, check for missing windows.')
parser.add_argument('--cf', type=file, dest='fClusteredFile', help='Enter the clustered file from the project.')
parser.add_argument('--list', type=bool,default=False, dest='bList', help='Set to \'True\' if you want the gene names.')
args = parser.parse_args()


def getSeqs(fileFasta):

    agSeqs = []
    
    for seq in SeqIO.parse(fileFasta, "fasta"):
        agSeqs.append(seq)
    
    return agSeqs

agClustSeqs = getSeqs(args.fClusteredFile)
agWindowSeqs = getSeqs(sys.stdin)

##############################################################################
#Prep Data

astrWindowNames = []
for i in agWindowSeqs:
    mtchName = re.search(r'(.*)(\_[TCQ]M[0-9]*)(\_\#[0-9]*)',i.id)
    strName = mtchName.group(1)
    astrWindowNames.append(strName)
    
astrClustNames = []
for i in agClustSeqs:
    astrClustNames.append(i.id)
        
dictCounts = Counter(astrWindowNames)
atupCounts = dictCounts.items()
aCounts = []

for tup in atupCounts:
    aCounts.append(tup[1])

#######################################################
#Tabs on Windows file

print "Total number of windows:"
print len(agWindowSeqs)

print "Breakdown of windows:"
print "(N, Number of genes with N windows)"
for x in Counter(aCounts).items():
    print x

#######################################################
#Check for missing genes

sClustNames = set(astrClustNames)
sWindowNames = set(astrWindowNames)


print "Unique genes in clustered file:"
print len(sClustNames)

print "Unique genes in windows file:"
print len(sWindowNames)


print "Number of genes in original clustered file that have 0 windows:"
print len(sClustNames.difference(sWindowNames))

if(args.bList):
    print "List of genes that have 0 windows:"
    for x in sClustNames.difference(sWindowNames):
        print x
    
    