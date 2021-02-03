# Portfolio Optimizer

This repo is a Django website for the portfolio optimization platform. Django is a python-based web framework with built-in database management API. This will help us efficiently store stock/financial data into a cloud database, but be able to easily access it using python and run whatever analysis we want. The results can then be stored and presented on this web platform.

I haven't set up the database yet, it just uses a sqlite3 as default, but it's pretty easy to use something more robust like postgres. 


I created a folder called optimizer. Here we can create whatever code necessary, such as:

1. an API script to download the latest stock data, 
2. a preprocessing algorithm for whatever data cleanup steps necessary, 
3. a prediction/forecasting model that predicts the potential return and risk, and 
4. an optimization step that optimizes the portfolio based on risk and potential return.
