import prediction
from pypfopt.efficient_frontier import EfficientFrontier



def meanvar(df):

    expected_returns = prediction.expected_returns()

    ef = EfficientFrontier(expected_returns, cov_matrix)  # setup
    ef.add_objective(objective_functions.L2_reg)  # add a secondary objective
    ef.min_volatility()  # find the portfolio that minimises volatility and L2_reg