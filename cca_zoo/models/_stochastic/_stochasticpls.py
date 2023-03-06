from typing import Union

import numpy as np

from cca_zoo.models._stochastic import RCCAEigenGame
from cca_zoo.models._stochastic._base import tv


class PLSStochasticPower(RCCAEigenGame):
    r"""
    A class used to fit Stochastic PLS

    Parameters
    ----------
    latent_dims : int, optional
        Number of latent dimensions to use, by default 1
    scale : bool, optional
        Whether to scale the data, by default True
    centre : bool, optional
        Whether to centre the data, by default True
    copy_data : bool, optional
        Whether to copy the data, by default True
    random_state : int, optional
        Random state to use, by default None
    accept_sparse : bool, optional
        Whether to accept sparse data, by default None
    batch_size : int, optional
        Batch size to use, by default 1
    shuffle : bool, optional
        Whether to shuffle the data, by default True
    sampler : torch.utils.data.Sampler, optional
        Sampler to use, by default None
    batch_sampler : torch.utils.data.Sampler, optional
        Batch sampler to use, by default None
    num_workers : int, optional
        Number of workers to use, by default 0
    pin_memory : bool, optional
        Whether to pin memory, by default False
    drop_last : bool, optional
        Whether to drop the last batch, by default True
    timeout : int, optional
        Timeout to use, by default 0
    worker_init_fn : function, optional
        Worker init function to use, by default None
    epochs : int, optional
        Number of epochs to use, by default 1
    learning_rate : float, optional
        Learning rate to use, by default 0.01

    References
    ----------
    Arora, Raman, et al. "Stochastic optimization for PCA and PLS." 2012 50th Annual Allerton Conference on Communication, Control, and Computing (Allerton). IEEE, 2012.

    """

    def __init__(
        self,
        latent_dims: int = 1,
        scale: bool = True,
        centre=True,
        copy_data=True,
        random_state=None,
        tol=1e-4,
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
        learning_rate=None,
        initialization: Union[str, callable] = "random",
    ):
        super().__init__(
            latent_dims=latent_dims,
            scale=scale,
            centre=centre,
            copy_data=copy_data,
            accept_sparse=accept_sparse,
            random_state=random_state,
            tol=tol,
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
            initialization=initialization,
            nesterov=False,
            line_search=False,
            ensure_descent=False,
        )

    def _update(self, views):
        for i, view in enumerate(views):
            self.weights[i] = self._gradient_descent(i, views, self.weights)
            self.weights_old[i] = self.weights[i].copy()
        return False

    def _gradient_descent(self, i, views, y):
        projections = np.ma.stack([view @ weight for view, weight in zip(views, y)])
        u = [y_.copy() for y_ in y]
        Aw, Bw, wAw, wBw = self._get_terms(i, views[i], projections, u[i])
        grad = self.grads(Aw, wAw, Bw, wBw)
        u = self._gradient_step(y[i], grad)
        return u

    def grads(self, Aw, wAw, Bw, wBw):
        return -Aw

    def _gradient_step(self, y, grad):
        return self._orth(y - self.learning_rate * grad)

    @staticmethod
    def _orth(U):
        Qu, Ru = np.linalg.qr(U)
        Su = np.sign(np.sign(np.diag(Ru)) + 0.5)
        return Qu @ np.diag(Su)

    def objective(self, views, **kwargs):
        q = [np.linalg.qr(weight)[0] for weight in self.weights]
        views = [self.scalers[i].transform(view) for i, view in enumerate(views)]
        transformed_views = []
        for i, (view) in enumerate(views):
            transformed_view = view @ q[i]
            transformed_views.append(transformed_view)
        return tv(transformed_views)
