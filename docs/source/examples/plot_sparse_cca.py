"""
Sparse CCA Comparison
===========================

This example demonstrates how to easily train Sparse CCA variants
"""

# Import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from cca_zoo._base import BaseModel
from cca_zoo.data.simulated import LinearSimulatedData
from cca_zoo.model_selection import GridSearchCV
from cca_zoo.linear import (
    CCA,
    PLS,
    SCCA_IPLS,
    SCCA_PMD,
    AltMaxVar,
    ElasticCCA,
    SCCA_Span,
)


def plot_true_weights_coloured(ax, weights, true_weights, title=""):
    ind = np.arange(len(true_weights))
    mask = np.squeeze(true_weights == 0)
    ax.scatter(ind[~mask], weights[~mask], c="b")
    ax.scatter(ind[mask], weights[mask], c="r")
    ax.set_title(title)


def plot_model_weights(wx, wy, tx, ty, title=""):
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    plot_true_weights_coloured(axs[0, 0], tx, tx, title="true x weights")
    plot_true_weights_coloured(axs[0, 1], ty, ty, title="true y weights")
    plot_true_weights_coloured(axs[1, 0], wx, tx, title="model x weights")
    plot_true_weights_coloured(axs[1, 1], wy, ty, title="model y weights")
    plt.tight_layout()
    fig.suptitle(title)
    plt.show()


# %%
# Data
# -----
np.random.seed(42)
n = 400
p = 100
q = 100
view_1_sparsity = 0.1
view_2_sparsity = 0.1
latent_dims = 1
epochs = 100

# Simulate some data with two views (X and Y) that have some correlation between them
data = LinearSimulatedData(
    view_features=[p, q],
    latent_dims=latent_dims,
    view_sparsity=[view_1_sparsity, view_2_sparsity],
    correlation=[0.95],
)
(X, Y) = data.sample(n)

tx = data.true_features[0]
ty = data.true_features[1]
tx /= np.sqrt(np.diag(np.atleast_1d(np.cov(X @ tx, rowvar=False))))
ty /= np.sqrt(np.diag(np.atleast_1d(np.cov(X @ ty, rowvar=False))))


class TrueWeights(BaseModel):
    def __init__(self, weights):
        super().__init__()
        self.weights = weights
        self.n_views_ = len(weights)
        self.n_features_ = [w.shape[0] for w in weights]


true = TrueWeights([tx, ty])

# Split the data into train and validation sets
X_train, X_val, Y_train, Y_val = train_test_split(X, Y, test_size=0.2)

# %% CCA
# CCA is a method that finds linear projections of the views that are maximally correlated
cca = CCA().fit([X_train, Y_train])
plot_model_weights(cca.weights[0], cca.weights[1], tx, ty, title="CCA")

# Evaluate the model on the validation set using correlation as a metric
cca_corr = cca.score([X_val, Y_val])
print(f"CCA correlation on validation set: {cca_corr}")

# %% PLS
# PLS is a method that finds linear projections of the views that are maximally covariant and have high variance in each view
pls = PLS().fit([X_train, Y_train])
plot_model_weights(pls.weights[0], pls.weights[1], tx, ty, title="PLS")

# Evaluate the model on the validation set using correlation as a metric
pls_corr = pls.score([X_val, Y_val])
print(f"PLS correlation on validation set: {pls_corr}")

# %% PMD
# PMD is a method that finds sparse linear projections of the views that are maximally correlated by using a penalty term on the weights
tau1 = [0.1, 0.3, 0.5]
tau2 = [0.1, 0.3, 0.5]
param_grid = {"tau": [tau1, tau2]}
pmd = GridSearchCV(SCCA_PMD(track="loss", epochs=epochs), param_grid=param_grid).fit(
    [X_train, Y_train]
)

# %%
plt.figure()
plt.title("Objective Convergence")
plt.plot(np.array(pmd.best_estimator_.objective))
plt.ylabel("Objective")
plt.xlabel("#iterations")
# %%
plot_model_weights(
    pmd.best_estimator_.weights[0], pmd.best_estimator_.weights[1], tx, ty, title="PMD"
)

# Evaluate the model on the validation set using correlation as a metric
pmd_corr = pmd.score([X_val, Y_val])
print(f"PMD correlation on validation set: {pmd_corr}")

# %%
pd.DataFrame(pmd.cv_results_)

# %% IPLS
# IPLS is a method that finds sparse linear projections of the views that are maximally covariant by using an iterative algorithm
scca = SCCA_IPLS(alpha=[1e-2, 1e-2], track="loss", epochs=epochs).fit(
    [X_train, Y_train]
)
plot_model_weights(scca.weights[0], scca.weights[1], tx, ty, title="SCCA_IPLS")

plt.figure()
plt.title("Objective Convergence")
plt.plot(np.array(scca.objective))
plt.ylabel("Objective")
plt.xlabel("#iterations")

# Evaluate the model on the validation set using correlation as a metric
scca_corr = scca.score([X_val, Y_val])
print(f"SCCA_IPLS correlation on validation set: {scca_corr}")

scca_pos = SCCA_IPLS(
    alpha=[1e-2, 1e-2], positive=[True, True], track="loss", epochs=epochs
).fit([X_train, Y_train])
plot_model_weights(
    scca_pos.weights[0], scca_pos.weights[1], tx, ty, title="SCCA_IPLS (Positive)"
)

plt.figure()
plt.title("Objective Convergence")
plt.plot(np.array(scca_pos.objective))
plt.ylabel("Objective")
plt.xlabel("#iterations")

# Evaluate the model on the validation set using correlation as a metric
scca_pos_corr = scca_pos.score([X_val, Y_val])
print(f"SCCA_IPLS (Positive) correlation on validation set: {scca_pos_corr}")

elasticcca = ElasticCCA(
    alpha=[1e-2, 1e-2], l1_ratio=[0.5, 0.5], track="loss", epochs=epochs
).fit([X_train, Y_train])
plot_model_weights(
    elasticcca.weights[0], elasticcca.weights[1], tx, ty, title="ELastic CCA"
)

plt.figure()
plt.title("Objective Convergence")
plt.plot(np.array(elasticcca.objective))
plt.ylabel("Objective")
plt.xlabel("#iterations")

# Evaluate the model on the validation set using correlation as a metric
elasticcca_corr = elasticcca.score([X_val, Y_val])
print(f"Elastic CCA correlation on validation set: {elasticcca_corr}")

altmaxvar = AltMaxVar(tau=[1e-2, 1e-2], track="loss", epochs=epochs).fit(
    [X_train, Y_train]
)
plot_model_weights(
    altmaxvar.weights[0], altmaxvar.weights[1], tx, ty, title="AltMaxVar"
)

plt.figure()
plt.title("Objective Convergence")
plt.plot(np.array(altmaxvar.objective))
plt.ylabel("Objective")
plt.xlabel("#iterations")

# Evaluate the model on the validation set using correlation as a metric
altmaxvar_corr = altmaxvar.score([X_val, Y_val])
print(f"AltMaxVar correlation on validation set: {altmaxvar_corr}")

# Add a comparison chart of all the models using validation correlation

# Create a list of model names and validation correlations
model_names = [
    "CCA",
    "PLS",
    "PMD",
    "SCCA_IPLS",
    "SCCA_IPLS (Positive)",
    "Elastic CCA",
    "AltMaxVar",
]
model_corrs = np.squeeze(
    np.array(
        [
            cca_corr,
            pls_corr,
            pmd_corr,
            scca_corr,
            scca_pos_corr,
            elasticcca_corr,
            altmaxvar_corr,
        ]
    )
)

# Plot a bar chart of model names and validation correlations
plt.figure()
plt.bar(model_names, model_corrs)
plt.xticks(rotation=90)
plt.ylabel("Validation correlation")
plt.title("Comparison of models")
plt.show()