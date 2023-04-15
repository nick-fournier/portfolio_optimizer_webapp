# Portfolio Optimizer

This is my attempt at making a crude stock portfolio and optimizing it. 

## How it works?
In general it is a "value investing" type of approach where you hold the stocks for at least a year. I could tighten the timeframe to quarterly, but company fundamental data are difficult to get for more than a year at that time period. 

I use company fundamentals to calculate and filter stocks using a [Piotroski F-Score](https://en.wikipedia.org/wiki/Piotroski_F-score). I then optimize the selected stocks in the portfolio using the [efficient frontier](https://en.wikipedia.org/wiki/Efficient_frontier) method of modern portoflio theory. The expected returns are estimated using a very crude autoregressive model using the same key fundamentals for calculating the Piotroski F-Score as features. 


## Tech stack
It created entirely in Django, a python-based web framework with built-in database management. Primarily, I use [yahooquery](https://yahooquery.dpguthrie.com/) to scrape financial data from Yahoo Finance and [pyportfolioopt](https://pyportfolioopt.readthedocs.io/en/latest/).