#!/usr/bin/env python
##!/work/local/bin/python
##!/work/local/CDAT/bin/python

import sys,getopt
import matplotlib.pyplot as plt


def read():

    x = []
    y = []
    for line in sys.stdin:
        v1,v2 = line.split()[:2]
        x.append(float(v1))
        y.append(float(v2))
    return x,y


#def plot(x,y):
def plot(x,y,xlabel,ylabel,title,fn):

    fig = plt.figure( figsize=(6.0,6.0) )
    ax = fig.add_subplot(111)
    ax.grid(True)
    if title:
        ax.set_title(title)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    plot = ax.scatter( x, y, s=3, marker='o' )

    mx = max(x)
    mn = min(x)
    plot = ax.plot( [mn,mx], [mn,mx] , 'r-')

    if fn:
        fname = fn
    else:
        fname = 'TMP_scat.png'
    fig.savefig( fname, format='png' )
    print 'WROTE --> %s' % fname



######################################
use = '''
Usage: %s 

    -h      help

'''
if __name__ == '__main__':

    def usage():
        sys.stderr.write(use % sys.argv[0])
        sys.exit(1)

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'hx:y:o:t:')
    except getopt.error:
        usage()

    fn = ''
    x = 'X'
    y = 'Y'
    title = ''
    for (opt,val) in opts:
        if opt == '-x':
            x = val
        elif opt == '-y':
            y = val
        elif opt == '-t':
            title = val
        elif opt == '-o':
            fn = val
        else:
            raise OptionError, opt
            usage()

    #if len(args) != 1:
    #   usage()
    #fn = args[0]

    xv,yv = read()
    plot(xv,yv,x,y,title,fn)

