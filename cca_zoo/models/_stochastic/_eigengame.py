import numpy as np

from cca_zoo.models._stochastic._base import _BaseStochastic
from cca_zoo.utils import _process_parameter


class RCCAEigenGame(_BaseStochastic):

    """

    References
    ----------
    Chapman, James, Ana Lawry Aguila, and Lennie Wells. "A Generalized EigenGame with Extensions to Multiview Representation Learning." arXiv preprint arXiv:2211.11323 (2022).
    """

    def __init__(
            self,
            latent_dims: int = 1,
            scale: bool = True,
            centre=True,
            copy_data=True,
            random_state=None,
            accept_sparse=None,
            batch_size=1,
            shuffle=True,
            sampler=None,
            batch_sampler=None,
            num_workers=0,
            pin_memory=False,
            drop_last=True,
            timeout=0,
            worker_init_fn=None,
            epochs=1,
            learning_rate=0.01,
            c=0,
    ):
        super().__init__(
            latent_dims=latent_dims,
            scale=scale,
            centre=centre,
            copy_data=copy_data,
            accept_sparse=accept_sparse,
            random_state=random_state,
            batch_size=batch_size,
            shuffle=shuffle,
            sampler=sampler,
            batch_sampler=batch_sampler,
            num_workers=num_workers,
            pin_memory=pin_memory,
            drop_last=drop_last,
            timeout=timeout,
            worker_init_fn=worker_init_fn,
            epochs=epochs,
            learning_rate=learning_rate,
        )
        self.c = c

    def _check_params(self):
        self.c = _process_parameter("c", self.c, 0, self.n_views)

    def update(self, views):
        projections = np.stack(
            [view @ weight for view, weight in zip(views, self.weights)]
        )
        for i, view in enumerate(views):
            projections = np.ma.array(projections, mask=False, keep_mask=False)
            projections.mask[i] = True
            Aw = self._Aw(view, projections.sum(axis=0).filled())
            projections.mask[i] = False
            Bw = self._Bw(view, projections[i].filled(), self.weights[i], self.c[i])
            grads = 2 * Aw - (Aw @ np.triu(self.weights[i].T @ Bw) + Bw @ np.triu(self.weights[i].T @ Aw))
            self.weights[i] += self.learning_rate * grads

    def _Aw(self, view, projections):
        return view.T @ projections / view.shape[0]

    def _Bw(self, view, projection, weight, c):
        return c * weight + (1 - c) * view.T @ projection / projection.shape[0]

    def objective(self, views, **kwargs):
        return self.tcc(views)


class CCAEigenGame(RCCAEigenGame):
    """

    References
    ----------
    Chapman, James, Ana Lawry Aguila, and Lennie Wells. "A Generalized EigenGame with Extensions to Multiview Representation Learning." arXiv preprint arXiv:2211.11323 (2022).
    """
    def __init__(
            self,
            *args, **kwargs,
    ):
        kwargs.pop('c', None)
        super().__init__(*args, c=0, **kwargs)


class PLSEigenGame(RCCAEigenGame):
    """

    References
    ----------
    Chapman, James, Ana Lawry Aguila, and Lennie Wells. "A Generalized EigenGame with Extensions to Multiview Representation Learning." arXiv preprint arXiv:2211.11323 (2022).
    """
    def __init__(
            self,
            *args, **kwargs,
    ):
        kwargs.pop('c', None)
        super().__init__(*args, c=1, **kwargs)

    def objective(self, views, **kwargs):
        return self.tv(views)