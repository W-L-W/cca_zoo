from typing import Iterable, Union

import numpy as np
import torch

from cca_zoo.linear._iterative._base import BaseIterative, BaseLoop
from cca_zoo.utils import _process_parameter


class AltMaxVar(BaseIterative):
    def __init__(
        self,
        latent_dimensions=1,
        copy_data=True,
        random_state=None,
        epochs=100,
        tol=1e-3,
        proximal="L1",
        positive=False,
        tau: Union[Iterable[float], float] = None,
        proximal_params: Iterable[dict] = None,
        gamma=0.1,
        learning_rate=0.1,
        T=100,
        trainer_kwargs=None,
        convergence_checking=None,
        track=None,
        verbose=False,
    ):
        super().__init__(
            latent_dimensions=latent_dimensions,
            copy_data=copy_data,
            random_state=random_state,
            tol=tol,
            epochs=epochs,
            convergence_checking=convergence_checking,
            track=track,
            verbose=verbose,
            trainer_kwargs=trainer_kwargs,
        )
        self.tau = tau
        self.proximal = proximal
        self.proximal_params = proximal_params
        self.gamma = gamma
        self.learning_rate = learning_rate
        self.T = T
        self.positive = positive
        # set trainer kwargs accelerator to 'cpu'
        self.trainer_kwargs["accelerator"] = "cpu"

    def _get_module(self, weights=None, k=None):
        return AltMaxVarLoop(
            weights=weights,
            k=k,
            gamma=self.gamma,
            T=self.T,
            proximal_operators=self.proximal_operators,
            learning_rate=self.learning_rate,
            convergence_checking=self.convergence_checking,
            track=self.track,
        )

    def _check_params(self):
        self.proximal = _process_parameter(
            "proximal", self.proximal, "L1", self.n_views_
        )
        self.positive = _process_parameter(
            "positive", self.positive, False, self.n_views_
        )
        self.tau = _process_parameter("tau", self.tau, 0, self.n_views_)
        self.sigma = self.tau
        self.proximal_operators = [
            self._get_proximal(view) for view in range(self.n_views_)
        ]

    def _get_proximal(self, view):
        if callable(self.proximal[view]):
            params = self.proximal_params[view] or {}
        else:
            params = {
                "sigma": self.sigma[view],
                "positive": self.positive[view],
            }
        return _proximal_operators(self.proximal[view], **params)

    def _more_tags(self):
        return {"multiview": True}


class AltMaxVarLoop(BaseLoop):
    def __init__(
        self,
        weights,
        k=None,
        gamma=0.1,
        T=100,
        proximal_operators=None,
        learning_rate=0.1,
        convergence_checking=None,
        track=None,
    ):
        super().__init__(
            weights=weights,
            k=k,
            convergence_checking=convergence_checking,
            tracking=track,
        )
        self.gamma = gamma
        self.proximal_operators = proximal_operators
        self.T = T
        self.learning_rate = learning_rate

    def forward(self, views: list) -> list:
        # views detach and numpy
        views = [view.detach().numpy() for view in views]
        return [view @ weight for view, weight in zip(views, self.weights)]

    def _get_target(self, scores):
        if hasattr(self, "G"):
            R = self.gamma * scores.mean(axis=0) + (1 - self.gamma) * self.G
        else:
            R = scores.mean(axis=0)
        U, S, Vt = np.linalg.svd(R, full_matrices=False)
        G = U @ Vt
        return G

    def objective(self, views, scores, weights) -> int:
        least_squares = (np.linalg.norm(scores - self.G, axis=(1, 2)) ** 2).sum()
        regularization = np.array(
            [
                self.proximal_operators[view](weights[view])
                for view in range(self.n_views)
            ]
        ).sum()
        return least_squares + regularization

    def training_step(self, batch, batch_idx):
        scores = np.stack(self(batch["views"]))
        self.G = self._get_target(scores)
        converged = False
        for i, view in enumerate(batch["views"]):
            view = view.detach().numpy()
            t = 0
            # initialize the previous weights to None
            prev_weights = None
            while t < self.T and not converged:
                # update the weights using the gradient descent and proximal operator
                self.weights[i] -= self.learning_rate * (
                    view.T @ (view @ self.weights[i] - self.G)
                )
                self.weights[i] = self.proximal_operators[i].prox(
                    self.weights[i], self.learning_rate
                )
                # check if the weights have changed significantly from the previous iteration
                if prev_weights is not None and np.allclose(
                    self.weights[i], prev_weights
                ):
                    # if yes, set converged to True and break the loop
                    converged = True
                    break
                # update the previous weights for the next iteration
                prev_weights = self.weights[i]
                t += 1

        # if track or convergence_checking is enabled, compute the objective function
        if self.tracking or self.convergence_checking:
            objective = self.objective(batch["views"])

            return {"loss": torch.tensor(objective)}


from pyproximal import (
    L0,
    L0Ball,
    L1,
    L1Ball,
    L2,
    L21,
    L21_plus_L1,
    Nuclear,
    NuclearBall,
    Log,
    Log1,
    Euclidean,
    EuclideanBall,
)

PROXIMAL_OPERATORS = {
    "L0": L0,
    "L0Ball": L0Ball,
    "L1": L1,
    "L1Ball": L1Ball,
    "L2": L2,
    "L21": L21,
    "L21_plus_L1": L21_plus_L1,
    "Nuclear": Nuclear,
    "NuclearBall": NuclearBall,
    "Log": Log,
    "Log1": Log1,
    "Euclidean": Euclidean,
    "EuclideanBall": EuclideanBall,
}

PROXIMAL_PARAMS = {
    "Dummy": (),
    "L0": frozenset(["sigma"]),
    "L0Ball": frozenset(["radius"]),
    "L1": frozenset(["sigma"]),
    "L1Ball": frozenset(["n", "radius"]),
    "L2": frozenset(["sigma"]),
    "L21": frozenset(["ndim", "sigma"]),
    "L21_plus_L1": frozenset(["sigma", "rho"]),
    "TV": frozenset(["sigma", "isotropic", "dims"]),
    "Nuclear": frozenset(["dim", "sigma"]),
    "NuclearBall": frozenset(["dims", "radius"]),
    "Log": frozenset(["sigma", "gamma"]),
    "Log1": frozenset(["sigma", "delta"]),
    "Euclidean": frozenset(["sigma"]),
    "TVL1": frozenset(["sigma", "shape", "l1_ratio"]),
}


def _proximal_operators(proximal, filter_params=True, **params):
    if proximal in PROXIMAL_OPERATORS:
        if filter_params:
            params = {k: params[k] for k in params if k in PROXIMAL_PARAMS[proximal]}
        return PROXIMAL_OPERATORS[proximal](**params)
    elif callable(proximal):
        return proximal(**params)