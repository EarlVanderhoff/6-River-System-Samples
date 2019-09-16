CMCHECKBPISTATE.PY is the first microservices app I wrote for Altice after onboarding. The only thing even remotely proprietary about it sould be the pckping, which is an in-house developed package that interrogates Altice cable modems over various means (SNMP, TR-069 and SSH). For obvious ethical concerns, I've intentionally not included this package.

The remainder of cmCheckBPIState is a simple SNMP interrogation of a cable modem's encryption status using information that is gleefully distributed about the web by manufacturers... nothing to see here folks.

Ditto for CMCMTSREST.PY. For this micro app I was asked to repeatedly reset a modem using CLI to the terminal server. Basic metrics developed (fastest, slowest, average, total, # successful, etc.)

Each of these is written as a class intended to be called from a basic OOP framework.

RVRVO_5G_DS.PY is the first Octoscope automation I put into place. It instantiates the necessary elements/objects and calls the test. It is notable for being much less flexible - I didn't write or refactor it as a class.

GRAPH_FILES.PY is included because I discussed it with Mr. Spero. It's a simple data visualization exercise, written to ingest Octoscope CSV files and output more useful data than what is obtainable from their own GUI. Octoscope doesn't provide RSSI-vs-Throughput graphing and I thought it would be of overt benefit, so I rolled my own. It's a class only in the most literal sense of the word... very sloppy... but still demonstrable. I included a data set to run it against if you wish (RvRvO 5G US.csv) and the resultant plot (example.xlsx). The data originates from tests against unnamed 3rd-party (non-Altice) CPE.

I can provide additional examples, encompassing different types of endeavors if desired.

Thanx All,
Earl
(401)523 3275


