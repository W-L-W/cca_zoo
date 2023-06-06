import numpy as np
import scipy.sparse as sp
from sklearn.utils import check_random_state

from cca_zoo.model_selection import (
    cross_validate,
    permutation_test_score,
    learning_curve,
)
from cca_zoo.models import PLS
from cca_zoo.plotting import pairplot_train_test

n = 50
rng = check_random_state(0)
X = rng.rand(n, 10)
Y = rng.rand(n, 11)
Z = rng.rand(n, 12)
X_sp = sp.random(n, 10, density=0.5, random_state=rng)
Y_sp = sp.random(n, 11, density=0.5, random_state=rng)
# centre the data
X -= X.mean(axis=0)
Y -= Y.mean(axis=0)
Z -= Z.mean(axis=0)
X_sp -= X_sp.mean(axis=0)
Y_sp -= Y_sp.mean(axis=0)


def test_explained_variance():
    # Test that explained variance is between 0 and 1
    pls = PLS(latent_dims=10).fit((X, X))
    explained_variance = pls.explained_variance_((X, X))
    explained_variance_ratio = pls.explained_variance_ratio_((X, X))
    # explained_variance_ratio should sum to 1 for each view
    assert np.allclose(explained_variance_ratio.sum(axis=1), 1)
    explained_variance_cumulative = pls.explained_variance_cumulative((X, X))
    # explained_variance_cumulative should be monotonically increasing
    assert np.all(np.diff(explained_variance_cumulative, axis=0) >= 0)


def test_explained_covariance():
    M = X @ X.T @ Y @ Y.T
    N = X.T @ Y
    # compare singular values of M and N
    u1, s1, v1 = np.linalg.svd(M)
    u2, s2, v2 = np.linalg.svd(N @ N.T)

    # Test that explained covariance is between 0 and 1
    pls = PLS(latent_dims=10).fit((X, X))
    explained_covariance = pls.explained_covariance_((X, X))
    explained_covariance_ratio = pls.explained_covariance_ratio_((X, X))
    # explained_covariance_ratio should sum to 1 for each view
    assert np.allclose(explained_covariance_ratio.sum(axis=1), 1)
    explained_covariance_cumulative = pls.explained_covariance_cumulative((X, X))
    # explained_covariance_cumulative should be monotonically increasing
    assert np.all(np.diff(explained_covariance_cumulative, axis=0) >= 0)


def test_validation():
    # Test that validation works
    pls = PLS(latent_dims=1).fit((X, Y))
    cross_validate(pls, (X, Y))
    permutation_test_score(pls, (X, Y))
    learning_curve(pls, (X, Y))


def test_plotting():
    pls = PLS(latent_dims=1).fit((X, Y))
    X_te = np.random.rand(*X.shape)
    Y_te = np.random.rand(*Y.shape)
    pairplot_train_test(pls.transform((X, Y)), pls.transform((X_te, Y_te)))
