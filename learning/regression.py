import numpy as np
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
    return list(y_pred), bool(reg.coef_[0] > 0)
