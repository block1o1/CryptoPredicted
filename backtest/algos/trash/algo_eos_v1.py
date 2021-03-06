
import json
import sys
sys.dont_write_bytecode = True

import numpy as np
import datetime
import random
import math
import core

def run(debug):

    # this strategy works best at 1hr intervals
    # 1. the idea is based on calculating the slope of the current price (which is a random price at interval 't') against the previous close price.
    # 2. it also makes sure a buy occurs when the current price is higher than the previous one
    # 3. 

    base = "BTC"
    #base = "ETH"
    #base = "LTC"

    quote = "USDT"
    historymins = 60*24*30*2 #60*24*30*4
    interval = 30
    dtend = datetime.datetime.strptime('2018-05-01 12:00', '%Y-%m-%d %H:%M')
    dtend = datetime.datetime.strptime('2018-05-26 12:00', '%Y-%m-%d %H:%M')
    dtstart = dtend - datetime.timedelta(minutes=historymins)
    inp = core.getPriceExchange_v1('binance', interval, base, quote, historymins, dtend)
    # inp = json.load(open("./LTC_60m.json"))
    uncertainty_margin = 0.001


    def EMAsingle(size, prevY, price):
        if len(prevY) == 0: return price
        multiplier = (2 / float(1 + size))
        v = price*multiplier + prevY[-1]*(1-multiplier)
        return v

    def sigA(y, z, price, hp_arrL, hp_arrEL):
        z.append(price)
        L = hp_arrL
        avg = np.average(z[-L:])
        std = np.std(z[-L:]) * 2
        out = avg + std
        out = EMAsingle(hp_arrEL, y, out)
        return out

    def sigC(y, z, price, hp_arrL, hp_arrEL):
        z.append(price)
        L = hp_arrL
        avg = np.average(z[-L:])
        std = np.std(z[-L:]) * 2
        out = avg - std
        out = EMAsingle(hp_arrEL, y, out)
        return out
    
    def work(_1, _2):
        portfolio = {}
        dtit = dtstart
        canBuy = True
        canSell = False

        traceA = core.createNewScatterTrace("traceA" ,"y")
        traceC = core.createNewScatterTrace("traceC" ,"y2", 'markers')
        traceD = core.createNewScatterTrace("traceD" ,"y2", 'markers')
        traceE = core.createNewScatterTrace("traceE" ,"y3")

        hp_arrL = 35
        hp_arrEL = 4

        usage = {
            'canBuy': True,
            'canSell': False,

            'buyPrice': None,
            'timeHeld': 0,
        }

        while dtit <= dtend:
            idx = datetime.datetime.strftime(dtit, '%Y-%m-%dT%H:%M')
            if idx in inp:
                volume = inp[idx]['volume']
                trades = inp[idx]['trades']
                c = inp[idx]['close']
                o = inp[idx]['open']
                l = inp[idx]['low']
                h = inp[idx]['high']


                #price = (o+c+l+h)/4   # ok
                price = (o+c)/2
                #price = c         # ok
                #price = o + (c-o)*random.randint(0,10)/10 # ok
                #price = random.uniform(o, c) if c > o else random.uniform(c, o) 
                #price = random.uniform(l, h)  # reality

                core.portfolioPriceEntry(portfolio, dtit, price, o, c, l, h)
            
                
                core.addToScatterTrace(traceA, dtit, (o+h+l+c)/4)
                pC = 1-1/(1+(price/np.average(traceA['y'][-24:])))
                core.addToScatterTrace(traceC, dtit, pC)

                core.addToScatterTrace(traceD, dtit, np.average(traceC['y'][-24:]))

                if len(traceD['y']) > 8:
                    pD = 1 if np.average(traceD['y'][-8:-4]) > np.average(traceD['y'][-4:-2]) and np.average(traceD['y'][-4:-2]) < np.average(traceD['y'][-2:]) else 0
                    #pD = 1 if traceD['y'][-1] > traceD['y'][-3] and traceD['y'][-2] < traceD['y'][-3] and traceD['y'][-2] < traceD['y'][-1] else 0
                    core.addToScatterTrace(traceE, dtit, pD )

                def buyF():
                    if len(traceE['y']) < 2: return False
                    
                    if traceE['y'][-2] == 0 and traceE['y'][-1]==1:
                        return True
                def sellF():
                    if traceD['y'][-1] < .5 and usage['timeHeld'] > 5:
                        return True

                    if price > usage['buyPrice']*_1: #and not buyF():
                        return True 
                    if price < usage['buyPrice']*_2:
                        return True

                if usage['canBuy'] and buyF():
                        core.portfolioBuy(portfolio, dtit, price, uncertainty_margin)
                        usage['canSell'] = True
                        usage['canBuy'] = False
                        usage['timeHeld'] = 0
                        usage['buyPrice'] = price
                elif usage['canSell'] and sellF():
                        core.portfolioSell(portfolio, dtit, price, uncertainty_margin)
                        usage['canSell'] = False
                        usage['canBuy'] = True
                        usage['timeHeld'] = 0
                        usage['sellPrice'] = price

                usage['timeHeld']+=1

                
            dtit += datetime.timedelta(minutes=interval)

        proc = core.processPortfolio(portfolio, 1)
        return (proc, portfolio, [traceA, traceC, traceD, traceE, ])


    if debug == 0:
        avgs = []
        for x in range(100):
            (proc, portfolio, traces) = work(1.03, 0.96)
            print("%s ROI \t %f" % (str(x), proc['_']['ROI%']))
            avgs.append(proc['_']['ROI%'])

        print("avg ROI%: " + str(sum(avgs)/len(avgs)))
        std = np.std(avgs)
        print("std ROI%: " + str(std))

    elif debug == 1: # brute-force searching for optimal parameters (A,B,C,D)
        dct = {}

        for A in [1+x/100 for x in range(1, 10)]:
            for B in [0.90+x/100 for x in range(1, 10)]:
                avgs = []
                for x in range(20):
                    (proc, portfolio, traces) = work(A,B)
                    avgs.append(proc['_']['ROI%'])

                print("%f %f" % (A,B))
                print("avg ROI%: " + str(sum(avgs)/len(avgs)))
                std = np.std(avgs)
                print("std ROI%: " + str(std))

                if not str(sum(avgs)/len(avgs)) in dct:
                    dct [ str(sum(avgs)/len(avgs)) ] = str(A)+"_"+str(B)
        print("--------")
        print(base)
        print("--------")
        print(json.dumps(dct))
        print("--------")
        print(base)
    
    else:
        shapes = [
            {
                'type': 'line',
                'xref': 'x',
                'yref': 'y2',
                'x0': datetime.datetime.strftime(dtstart, '%Y-%m-%dT%H:%M'),
                'x1': datetime.datetime.strftime(dtend, '%Y-%m-%dT%H:%M'),
                'y0': .50,
                'y1': .50,
                'line': {
                    'color': 'gray',
                    'width': 3,
                    'dash': 'dash'
                },
            },
        ]

        (proc, portfolio, traces) = work(1.02, 0.97)
        print("ROI: %f" % proc['_']['ROI%'])
        core.portfolioToChart_OHLC(portfolio, traces, shapes=shapes)

if __name__ == '__main__':
    debug = 2
    run(debug)