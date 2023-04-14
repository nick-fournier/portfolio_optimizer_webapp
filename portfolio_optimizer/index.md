# Portfolio Optimizer

This repo is a Django website for the portfolio optimization platform. Django is a python-based web framework with built-in database management API. This will help us efficiently store stock/financial data into a cloud database, but be able to easily access it using python and run whatever analysis we want. The results can then be stored and presented on this web platform.

So far this just has a basic home page with a simple login/logout/reset password functionality. Next I want to connect it to a database like postgreSQL. https://www.heroku.com/ has a lot of built in support for django and postgres already, and you can just deploy updates through git directly to it. Eventually I want to try hosting something there.

I created a folder called optimizer within the Django folder where we can place whatever python code we want. Django can then import those using the python module system and run them. I made a couple empty files for things I think we'd need:

1. an API script to download the latest stock data, 
2. a preprocessing algorithm for whatever data cleanup steps necessary, 
3. a prediction/forecasting model that predicts the potential return and risk, and 
4. an optimization step that optimizes the portfolio based on risk and potential return.

