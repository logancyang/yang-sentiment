import numpy as np
import statsmodels.api as sm
from sklearn import linear_model


# pylint: disable=logging-fstring-interpolation
def linear_regression(X, y):
    """Perform basic OLS linear regression on 1D data and returns predicted y
    values as a list. Return the predicted values and whether the coefficient is positive

    Arguments:
        X {list} -- 1D list of x values
        y {list} -- 1D list of y values
    """
    X_array = np.array(X)
    X_reshaped = X_array.reshape(-1, 1)
    reg = linear_model.LinearRegression()
    reg.fit(X_reshaped, y)
    y_pred = reg.predict(X_reshaped)
    return list(y_pred), _get_signif_delta(first=y_pred[0], last=y_pred[-1])

def stats_linear_regression(t, y):
    """Perform basic OLS linear regression on 1D data and returns predicted y
    values as a list. Return the predicted values and the trend value,
    0 for insignificant, 1 for positive, -1 for negative

    Arguments:
        X {list} -- 1D list of x values
        y {list} -- 1D list of y values
    """
    t, y = np.array(t), np.array(y)
    t = sm.add_constant(t)
    model = sm.OLS(y, t).fit()
    y_pred = model.predict(t)
    return list(y_pred), _get_signif(model.params[1], model.pvalues[1])

def _get_signif(coeff, pvalue):
    if pvalue >= 0.1:
        return 0
    if coeff > 0:
        return 1
    return -1

def _get_signif_delta(first, last, sensitivity=0.05):
    if last > first * (1 + sensitivity):
        return 1
    elif last < first * (1 - sensitivity):
        return -1
    return 0

"""Normalization and standardization do not affect regression inference p values"""
def _normalize(nparray):
    return (nparray - min(nparray)) / (max(nparray) - min(nparray))

def _standardize(nparray):
    return (nparray - np.mean(nparray)) / np.std(nparray)
