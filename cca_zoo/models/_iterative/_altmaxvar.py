import warnings
from typing import Union

import numpy as np

from .._rcca import rCCA
from ._base import _BaseInnerLoop
from ._base import _BaseIterative


class AltMaxVar(_BaseIterative):
    r"""


    .. math::

        w_{opt}, t_{opt}=\underset{w,t}{\mathrm{argmax}}\{\sum_i \|X_iw_i-t\|^2 + c\|w_i\|^2_2 + \text{l1_ratio}\|w_i\|_1\}\\

        \text{subject to:}

        t^Tt=n

    :Citation:

        Fu, Xiao, et al. "Scalable and flexible multiview MAX-VAR canonical correlation analysis." IEEE Transactions on Signal Processing 65.16 (2017): 4150-4165.


    :Example:

    """

    def __init__(
            self,
            latent_dims: int = 1,
            scale: bool = True,
            centre=True,
            copy_data=True,
            random_state=None,
            max_iter: int = 100,
            initialization: Union[str, callable] = "pls",
            tol: float = 1e-9,
            view_regs=None,
    ):
        """
        Constructor for ElasticCCA

        :param latent_dims: number of latent dimensions to fit
        :param scale: normalize variance in each column before fitting
        :param centre: demean data by column before fitting (and before transforming out of sample
        :param copy_data: If True, X will be copied; else, it may be overwritten
        :param random_state: Pass for reproducible output across multiple function calls
        :param max_iter: the maximum number of iterations to perform in the inner optimization loop
        :param initialization: either string from "pls", "cca", "random", "uniform" or callable to initialize the score variables for _iterative methods
        :param tol: tolerance value used for early stopping
        """
        super().__init__(
            latent_dims=latent_dims,
            scale=scale,
            centre=centre,
            copy_data=copy_data,
            max_iter=max_iter,
            initialization=initialization,
            tol=tol,
            random_state=random_state,
        )
        self.view_regs = view_regs

    def _outer_loop(self, views):
        self._set_loop_params()
        self.loop = self.loop._fit(
            views,
            initial_scores=self._initialization(
                views, self.initialization, self.random_state, self.latent_dims
            ),
        )
        for i, view in enumerate(views):
            self.weights[i] = self.loop.weights[i]
        self.track = self.loop.track
        if not self.track["converged"]:
            warnings.warn(f"Inner loop not converged. Increase number of iterations.")

    def _set_loop_params(self):
        self.loop = _AltMaxVarLoop(
            max_iter=self.max_iter,
            tol=self.tol,
            random_state=self.random_state,
            view_regs=self.view_regs,
        )

    def _initialization(self, views, initialization, random_state, latent_dims):
        if initialization == "random":
            return np.array(
                [random_state.normal(0, 1, size=(view.shape[0])) for view in views]
            )
        elif initialization == "uniform":
            return np.array([np.ones((view.shape[0], latent_dims)) for view in views])
        elif initialization == "pls":
            pls_scores = rCCA(latent_dims, c=1).fit_transform(views)
            return np.stack(pls_scores)
        elif initialization == "cca":
            cca_scores = rCCA(latent_dims).fit_transform(views)
            return np.stack(cca_scores)
        else:
            raise ValueError(
                "Initialization {type} not supported. Pass a generator implementing this method"
            )


class _AltMaxVarLoop(_BaseInnerLoop):
    def __init__(
            self,
            max_iter: int = 100,
            tol=1e-9,
            random_state=None,
            view_regs=None,
            alpha=1e-3,
    ):
        super().__init__(
            max_iter=max_iter,
            tol=tol,
            random_state=random_state,
        )
        self.alpha = alpha
        self.view_regs = view_regs

    def _inner_iteration(self, views):
        # Update each view using loop update function
        self._update_target()
        for i, view in enumerate(views):
            # if no nans
            if np.isnan(self.scores).sum() == 0:
                self._update_view(views, i)

    def _update_target(self):
        R = self.scores.sum(axis=0)
        U, _, Vt = np.linalg.svd(R, full_matrices=False)
        self.G = U @ Vt

    def _update_view(self, views, view_index: int):
        """
        :param view_index: index of view being updated
        :return: updated weights
        """
        self.weights[view_index] = self.view_regs[view_index](
            views[view_index], self.G, self.weights[view_index]
        )

    def _objective(self, views):
        total_objective = 0
        for i, _ in enumerate(views):
            objective = np.linalg.norm(views[i] @ self.weights[i] - self.G) ** 2 / (
                    2 * self.n
            )
            total_objective += objective + self.view_regs[i].cost(
                views[i], self.weights[i]
            )
        return total_objective

    def _initialize(self, views):
        self.weights = [
            np.zeros((view.shape[1], self.scores[0].shape[1])) for view in views
        ]

    def _early_stop(self) -> bool:
        # Some kind of early stopping
        if (self.track["objective"][-2] - self.track["objective"][-1]) < 1e-9:
            return True
        else:
            return False